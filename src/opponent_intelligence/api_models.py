"""Optional HTTP boundary models; analytical definitions remain in core builders."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class EvidenceQuery(BaseModel):
    """Shared HTTP parsing and cost bounds for the two evidence contracts."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    team: str = Field(pattern=r"^[A-Z]{2,3}$", min_length=2, max_length=3)
    season: int = Field(ge=1999, le=9999)
    before_week: int = Field(ge=1, le=23, description="Exclusive week cutoff.")
    season_type: Literal["REG", "POST"] = "REG"
    minimum_plays: int = Field(default=30, ge=1, le=100000)
    yardline_min: float | None = Field(default=None, ge=0, le=100)
    yardline_max: float | None = Field(default=None, ge=0, le=100)
    score_min: int | None = Field(default=None, ge=-1000, le=1000)
    score_max: int | None = Field(default=None, ge=-1000, le=1000)
    period: Literal["Q1", "Q2", "Q3", "Q4", "OT"] | None = None
    clock_min: int | None = Field(default=None, ge=0, le=900)
    clock_max: int | None = Field(default=None, ge=0, le=900)
    compare_league: Literal["true", "false"] = "false"
    bootstrap_repetitions: int | None = Field(default=None, ge=200, le=1000)
    bootstrap_seed: int | None = Field(default=None, ge=0, le=4294967295)

    @model_validator(mode="after")
    def consistent_options(self):
        for lower, upper in ((self.yardline_min, self.yardline_max),
                             (self.score_min, self.score_max), (self.clock_min, self.clock_max)):
            if lower is not None and upper is not None and lower > upper:
                raise ValueError("minimum must not exceed maximum")
        if self.period is None and (self.clock_min is not None or self.clock_max is not None):
            raise ValueError("clock bounds require a period")
        if self.bootstrap_seed is not None and self.bootstrap_repetitions is None:
            raise ValueError("bootstrap seed requires repetitions")
        return self

    def builder_options(self) -> dict:
        return {**self.model_dump(), "compare_league": self.compare_league == "true"}


class ReportQuery(EvidenceQuery):
    side: Literal["offense", "defense"] = "offense"


class DecisionQuery(EvidenceQuery):
    down: int = Field(ge=1, le=4)
    distance_min: int = Field(ge=0, le=100)
    distance_max: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def ordered_distance(self):
        if self.distance_min > self.distance_max:
            raise ValueError("distance_min must not exceed distance_max")
        return self


class OutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Metrics(OutputModel):
    plays: int = Field(ge=0)
    games: int = Field(ge=0)
    dropbacks: int = Field(ge=0)
    designed_runs: int = Field(ge=0)
    epa_observations: int = Field(ge=0)
    missing_epa: int = Field(ge=0)
    dropback_rate: float | None = Field(ge=0, le=1)
    success_rate: float | None = Field(ge=0, le=1)
    epa_per_play: float | None
    small_sample: bool
    small_epa_sample: bool


class Situation(Metrics):
    down: int = Field(ge=1, le=4)
    distance: Literal["short", "medium", "long"]


class Source(OutputModel):
    label: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot: dict[str, JsonValue]


class ReportResponse(OutputModel):
    """Exact v2 envelope; variable context/method blocks retain the core contract.

    This is transport shape validation, not a second statistical implementation.
    exclude_unset preserves absent opt-in blocks while retaining measured nulls.
    """

    schema_version: Literal[2]
    source: Source
    cohort: dict[str, JsonValue]
    metric_context: dict[str, JsonValue]
    data_quality: dict[str, JsonValue]
    overall: Metrics
    situations: list[Situation]
    warnings: list[str]
    league_comparison: dict[str, JsonValue] | None = None
    uncertainty: dict[str, JsonValue] | None = None


class CandidateAvailability(OutputModel):
    frequency: Literal["available", "empty_cohort"]
    outcomes: Literal["available", "empty_cohort", "unobserved_candidate", "missing_epa"]


class CandidateEvidence(OutputModel):
    candidate: Literal["run", "pass"]
    label: str
    mapping: dict[str, JsonValue]
    plays: int = Field(ge=0)
    games: int = Field(ge=0)
    epa_observations: int = Field(ge=0)
    missing_epa: int = Field(ge=0)
    epa_per_play: float | None
    success_rate: float | None = Field(ge=0, le=1)
    small_sample: bool
    small_epa_sample: bool
    frequency: float | None = Field(ge=0, le=1)
    frequency_denominator: int = Field(ge=0)
    availability: CandidateAvailability


class BaselineCandidate(CandidateEvidence):
    coverage: dict[str, JsonValue]
    difference: dict[str, float | None]


class CandidateLeagueComparison(OutputModel):
    population: dict[str, JsonValue]
    cohort: dict[str, JsonValue]
    difference_convention: Literal["selected_minus_baseline"]
    difference_units: dict[str, str]
    data_quality: dict[str, JsonValue]
    candidates: list[BaselineCandidate] = Field(min_length=2, max_length=2)
    warnings: list[str]


class DecisionComparison(OutputModel):
    status: Literal["insufficient_evidence"]
    preferred_candidate: None
    reason: Literal["candidate_comparison_not_validated"]
    policy_version: Literal["descriptive_only_v1"]
    descriptive_contrast: dict[str, JsonValue]
    opponent_evidence: dict[str, JsonValue]


class DecisionPopulation(OutputModel):
    plays: int = Field(ge=0)
    games: int = Field(ge=0)


class DecisionResponse(OutputModel):
    """Contract-v1 transport shape, without recomputing statistical identities.

    Counts/rates, availability and mandatory abstention are typed. Variable
    context/method blocks retain the core contract, just as in Scout responses.
    """

    contract_version: Literal[1]
    evidence_kind: Literal["descriptive_observed_calls"]
    source: Source
    cohort: dict[str, JsonValue]
    metric_context: dict[str, JsonValue]
    estimation_policy: dict[str, JsonValue]
    population: DecisionPopulation
    data_quality: dict[str, JsonValue]
    candidates: list[CandidateEvidence] = Field(min_length=2, max_length=2)
    comparison: DecisionComparison
    warnings: list[str]
    league_comparison: CandidateLeagueComparison | None = None
    uncertainty: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def candidate_order(self):
        populations = [self.candidates]
        if self.league_comparison is not None:
            populations.append(self.league_comparison.candidates)
        for candidates in populations:
            if [candidate.candidate for candidate in candidates] != ["run", "pass"]:
                raise ValueError("candidates must be Run then Pass")
        return self


class ErrorDetail(OutputModel):
    code: str
    message: str
    fields: list[str]


class ErrorResponse(OutputModel):
    error: ErrorDetail
