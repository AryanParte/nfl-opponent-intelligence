"""Actual image/HTTP checks with invented snapshots; requires a built Docker image.

PYTHONPATH=src NFL_OI_CONTAINER_IMAGE=nfl-oi-api:test python -m unittest discover -s tests_container -v
Uses invented data and standard-library clients. Main checks disable networking;
one recipe check publishes an ephemeral port exclusively on host loopback.
"""

import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import tomllib
import unittest
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.ingestion import load_snapshot
from opponent_intelligence.report import build_report
from opponent_intelligence.snapshots import ASSET_NAME
from tests_api.synthetic_snapshot import write_snapshot

ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get("NFL_OI_CONTAINER_IMAGE", "nfl-oi-api:test")
LABEL = "SYNTHETIC container fixture; invented plays and acquisition metadata, not real NFL observations"
QUERY = dict(team="CAR", season=2024, before_week=3)
DECISION = QUERY | dict(down=1, distance_min=10, distance_max=10)


def docker(*args, timeout=60, check=True):
    return subprocess.run(["docker", *args], cwd=ROOT, text=True, capture_output=True,
                          timeout=timeout, check=check)


class ContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docker("image", "inspect", IMAGE)  # No implicit pull or build.
        temporary = tempfile.TemporaryDirectory(prefix="nfl-oi-container-synthetic-")
        cls.addClassCleanup(temporary.cleanup)
        cls.root = Path(temporary.name)
        cls.root.chmod(0o755)  # The image's non-root UID must be able to read it.
        with (ROOT / "tests/fixtures/synthetic_pbp.csv").open(newline="") as stream:
            rows = [row for row in csv.DictReader(stream) if row["season"] == "2024"]
        cls.snapshot = write_snapshot(cls.root, rows, list(rows[0]))
        cls.dataset = load_snapshot(cls.snapshot)
        cls.fingerprints = {p.name: sha256(p.read_bytes()).hexdigest() for p in cls.snapshot.iterdir()}
        cls.environment = {"NFL_OI_SNAPSHOT": f"/snapshots/{cls.snapshot.name}", "NFL_OI_SOURCE_LABEL": LABEL}
        cls.container = cls.start_container(cls.environment)
        cls.wait_healthy(cls.container)

    @classmethod
    def wait_healthy(cls, container):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            state = json.loads(docker("inspect", container).stdout)[0]["State"]
            if not state["Running"]:
                raise AssertionError(docker("logs", container).stdout + docker("logs", container).stderr)
            if state.get("Health", {}).get("Status") == "healthy":
                break
            time.sleep(.25)
        else:
            raise AssertionError("container never became healthy: " + docker("logs", container).stderr)

    @classmethod
    def start_container(cls, environment, *, publish=False):
        name = "nfl-oi-test-" + uuid4().hex
        # Register cleanup before creation; a timed-out client may still create it.
        cls.addClassCleanup(cls.remove_container, name)
        args = ["create", "--name", name, "--read-only", "--network", "bridge" if publish else "none",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--pids-limit", "64", "--memory", "512m", "--cpus", "1",
                "--mount", f"type=bind,source={cls.root},target=/snapshots,readonly"]
        if publish:
            args.extend(["--publish", "127.0.0.1::8000"])
        for key, value in environment.items():
            args.extend(["--env", f"{key}={value}"])
        docker(*args, IMAGE)
        docker("start", name)
        return name

    @staticmethod
    def remove_container(name):
        result = docker("rm", "--force", name, check=False)
        # A failed creation has nothing to remove; surface other cleanup failures.
        if result.returncode and "No such container:" not in result.stderr:
            raise RuntimeError(f"failed to remove owned container {name}: {result.stderr}")

    def execute(self, code, *args):
        return docker("exec", self.container, "python", "-c", code, *args).stdout

    def request(self, route, query, *, method="GET", body=None):
        # All requests originate inside a network-none container, over loopback.
        code = """
import json,sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError
request=Request('http://127.0.0.1:8000'+sys.argv[1],method=sys.argv[2],
                data=None if sys.argv[3]=='none' else b'{}')
try:
    response=urlopen(request,timeout=5)
except HTTPError as error:
    response=error
with response:
    print(json.dumps({'status':response.status,'body':json.load(response)}))
"""
        return json.loads(self.execute(code, route + "?" + urlencode(query), method, "none" if body is None else "body"))

    def test_build_context_and_reviewed_dependency_inputs(self):
        manifest = json.loads((ROOT / "docker/api-inputs.json").read_text())
        versions = {r["name"]: r["version"] for r in manifest["wheels"]}
        bases = [line.split()[1] for line in (ROOT / "docker/api.Dockerfile").read_text().splitlines()
                 if line.startswith("FROM ") and not line.startswith("FROM scratch ")]
        self.assertEqual(bases, [manifest["base"], manifest["base"]])
        constraints = dict(line.split("==") for line in (ROOT / "requirements/api-constraints.txt").read_text().splitlines()
                           if line and not line.startswith("#"))
        self.assertTrue(all(constraints[name] == version for name, version in versions.items()))
        extras = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["optional-dependencies"]["api"]
        self.assertTrue(all(versions[name] == version for name, version in (item.split("==") for item in extras)))
        lock = (ROOT / "docker/api-requirements.lock").read_text()
        expected = {name: {r["sha256"] for r in manifest["wheels"] if r["name"] == name} for name in versions}
        actual = {}
        for line in lock.splitlines():
            if not line or line.startswith("#"):
                continue
            spec, *hashes = line.split(); name, version = spec.split("==")
            self.assertEqual(version, versions[name])
            self.assertNotIn(name, actual)
            actual[name] = {value.removeprefix("--hash=sha256:") for value in hashes}
        self.assertEqual(actual, expected)
        with tempfile.TemporaryDirectory(prefix="nfl-oi-context-") as export:
            docker("build", "--target", "context-audit", "-f", "docker/api.Dockerfile",
                   "--output", f"type=local,dest={export}", ".", timeout=120)
            context = Path(export) / "context"
            included = {str(p.relative_to(context)) for p in context.rglob("*") if p.is_file()}
            allowed = {"docker/api.Dockerfile", "docker/api.Dockerfile.dockerignore",
                       "docker/api-requirements.lock", "docker/api-inputs.json"}
            allowed |= {str(p.relative_to(ROOT)) for p in (ROOT / "src/opponent_intelligence").glob("*.py")}
            self.assertEqual(included, allowed)
            for name in included:
                self.assertEqual((context / name).read_bytes(), (ROOT / name).read_bytes())

    def test_image_identity_sources_and_runtime_wheels(self):
        image = json.loads(docker("image", "inspect", IMAGE).stdout)[0]
        self.assertEqual(image["Config"]["User"], "10001:10001")
        self.assertEqual(image["Config"]["Cmd"], ["python", "-m", "uvicorn", "opponent_intelligence.api:app_from_env",
                         "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--lifespan", "on", "--no-proxy-headers"])
        code = """
from hashlib import sha256
from importlib.metadata import distributions
import json,os,sys
from pathlib import Path
print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'python':list(sys.version_info[:2]),
 'versions':{d.metadata['Name'].lower().replace('_','-'):d.version for d in distributions(path=['/opt/api-deps'])},
 'source':{str(p.relative_to('/app/opponent_intelligence')):sha256(p.read_bytes()).hexdigest() for p in Path('/app/opponent_intelligence').rglob('*') if p.is_file()},
 'files':sorted(p.name for p in Path('/app').iterdir())}))
"""
        info = json.loads(self.execute(code))
        self.assertEqual((info["uid"], info["gid"], info["python"]), (10001, 10001, [3, 13]))
        manifest = json.loads((ROOT / "docker/api-inputs.json").read_text())
        self.assertEqual(info["versions"], {r["name"]: r["version"] for r in manifest["wheels"]})
        self.assertEqual(info["source"], {p.name: sha256(p.read_bytes()).hexdigest() for p in (ROOT / "src/opponent_intelligence").glob("*.py")})
        self.assertEqual(info["files"], ["opponent_intelligence"])
        self.assertEqual(json.loads(self.execute("import json; print(open('/usr/share/nfl-oi/api-inputs.json').read())")), manifest)

    def test_documented_loopback_publish_recipe(self):
        container = self.start_container(self.environment, publish=True)
        self.wait_healthy(container)
        ports = json.loads(docker("inspect", container).stdout)[0]["NetworkSettings"]["Ports"]["8000/tcp"]
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0]["HostIp"], "127.0.0.1")
        # Avoid inherited host proxy settings: this must be a direct loopback request.
        opener = build_opener(ProxyHandler({}))
        url = f"http://127.0.0.1:{ports[0]['HostPort']}/v1/decision?" + urlencode(DECISION)
        with opener.open(url, timeout=5) as response:
            self.assertEqual(response.status, 200)
            data = json.load(response)
        self.assertEqual(data, build_decision_evidence(self.dataset, DecisionRequest(**DECISION), source_label=LABEL))

    def test_read_only_mount_root_and_no_external_network(self):
        info = json.loads(docker("inspect", self.container).stdout)[0]
        self.assertTrue(info["HostConfig"]["ReadonlyRootfs"])
        self.assertEqual(info["HostConfig"]["NetworkMode"], "none")
        self.assertEqual(info["HostConfig"]["PortBindings"], {})
        self.assertFalse(info["Mounts"][0]["RW"])
        code = """
import errno,json,os,socket
from pathlib import Path
assert os.getuid()==10001
for target in ('/tmp/container-write-probe',os.environ['NFL_OI_SNAPSHOT']+'/manifest.json'):
    try:
        descriptor=os.open(target,os.O_WRONLY|os.O_CREAT,0o600)
    except OSError as error:
        assert error.errno in (errno.EROFS,errno.EACCES),error
    else:
        os.close(descriptor)
        raise AssertionError('unexpected writable path: '+target)
status=Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\t1' in status
assert 'CapEff:\t0000000000000000' in status
with socket.socket() as sock:
    sock.settimeout(1)
    assert sock.connect_ex(('192.0.2.1',443))!=0
print('read-only and isolated')
"""
        self.assertIn("read-only and isolated", self.execute(code))
        self.assertEqual({p.name: sha256(p.read_bytes()).hexdigest() for p in self.snapshot.iterdir()}, self.fingerprints)

    def test_scout_and_decision_keep_complete_core_evidence(self):
        for options in ({}, {"compare_league": True, "bootstrap_repetitions": 200, "bootstrap_seed": 7}):
            wire = {k: str(v).lower() if isinstance(v, bool) else v for k, v in options.items()}
            for side in ("offense", "defense"):
                result = self.request("/v1/report", QUERY | wire | {"side": side})
                self.assertEqual(result["status"], 200)
                self.assertEqual(result["body"], build_report(self.dataset, **QUERY, side=side, source_label=LABEL, **options))
            result = self.request("/v1/decision", DECISION | wire)
            self.assertEqual(result["status"], 200)
            self.assertEqual(result["body"], build_decision_evidence(self.dataset, DecisionRequest(**(DECISION | options)), source_label=LABEL))
            self.assertEqual(result["body"]["population"], {"plays": 3, "games": 2})
            run, passed = result["body"]["candidates"]
            self.assertEqual((run["plays"], passed["plays"]), (1, 2))
            self.assertEqual((run["epa_per_play"], run["success_rate"]), (0, 0))
            self.assertAlmostEqual(passed["epa_per_play"], .6)
            self.assertIsNone(result["body"]["comparison"]["preferred_candidate"])

    def test_empty_error_and_expensive_option_boundaries(self):
        for route, query in (("/v1/report", QUERY), ("/v1/decision", DECISION)):
            with self.subTest(route=route):
                result = self.request(route, query | {"before_week": 1})
                self.assertEqual(result["status"], 200)
                if route.endswith("report"):
                    self.assertIsNone(result["body"]["overall"]["epa_per_play"])
                else:
                    self.assertIsNone(result["body"]["candidates"][0]["frequency"])
                for options in ({"bootstrap_repetitions": 1001}, {"snapshot": "/private/secret"}, {"season": 2023}):
                    rejected = self.request(route, query | options)
                    self.assertEqual(rejected["status"], 422)
                    self.assertNotIn("/private/secret", json.dumps(rejected["body"]))
                self.assertEqual(self.request(route, query, method="POST")["status"], 405)
                self.assertEqual(self.request(route, query, body={})["status"], 400)

    def test_startup_requires_explicit_valid_snapshot_and_label(self):
        bad_root = self.root / "corrupt"
        bad_root.mkdir()
        corrupt = bad_root / self.snapshot.name
        shutil.copytree(self.snapshot, corrupt)
        (corrupt / ASSET_NAME).write_bytes(b"corrupt synthetic archive")
        cases = {
            "missing_environment": {},
            "missing_label": {"NFL_OI_SNAPSHOT": self.environment["NFL_OI_SNAPSHOT"]},
            "blank_label": self.environment | {"NFL_OI_SOURCE_LABEL": " "},
            "relative_path": self.environment | {"NFL_OI_SNAPSHOT": "relative"},
            "missing_snapshot": self.environment | {"NFL_OI_SNAPSHOT": "/snapshots/missing"},
            "corrupt_snapshot": self.environment | {"NFL_OI_SNAPSHOT": f"/snapshots/corrupt/{self.snapshot.name}"},
        }
        for name, environment in cases.items():
            with self.subTest(case=name):
                container = self.start_container(environment)
                result = docker("wait", container, timeout=20)
                self.assertNotEqual(int(result.stdout.strip()), 0)
                logs = docker("logs", container)
                self.assertNotIn("Application startup complete", logs.stdout + logs.stderr)
        self.assertEqual({p.name: sha256(p.read_bytes()).hexdigest() for p in self.snapshot.iterdir()}, self.fingerprints)

    def test_graceful_shutdown_releases_the_single_process(self):
        container = self.start_container(self.environment)
        self.wait_healthy(container)
        docker("stop", "--time", "5", container)
        state = json.loads(docker("inspect", container).stdout)[0]["State"]
        self.assertFalse(state["Running"])
        self.assertIn(state["ExitCode"], (0, 143))
        self.assertIn("Application shutdown complete", docker("logs", container).stderr)


if __name__ == "__main__":
    unittest.main()
