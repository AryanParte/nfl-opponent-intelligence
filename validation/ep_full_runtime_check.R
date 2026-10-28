# Offline installed-reference check, not prediction or numerical-parity evidence.
# Mount the verified acquisition at /artifact and this file read-only at /probe.R.
options(warn = 2)
hash <- function(path) {
  out <- system2("sha256sum", shQuote(path), stdout = TRUE)
  stopifnot(is.null(attr(out, "status")), length(out) == 1L)
  substr(out, 1L, 64L)
}
root <- "/opt/ep-runtime"
source_lock <- jsonlite::fromJSON(file.path(root, "ep_runtime.lock.json"), simplifyVector = FALSE)
native_lock <- jsonlite::fromJSON(file.path(root, "ep_native.lock.json"), simplifyVector = FALSE)
native <- jsonlite::fromJSON(file.path(root, "native-installation.json"), simplifyVector = FALSE)
stopifnot(as.character(getRversion()) == source_lock$r_version,
          native$native_lock_sha256 == hash(file.path(root, "ep_native.lock.json")),
          native$upgraded == 0L, native$removed == 0L, length(native$added) == 7L)
for (p in source_lock$packages) stopifnot(as.character(packageVersion(p$package)) == p$version)
for (p in native_lock$packages) stopifnot(hash(p$copyright_path) == p$copyright_sha256)
stopifnot(requireNamespace("nflfastR", quietly = TRUE), requireNamespace("fastrmodels", quietly = TRUE))
invisible(xgboost::xgb.set.config(nthread = 1L))
stopifnot(xgboost::xgb.get.config()$nthread == 1L)

# Compare raw bytes, without constructing a booster or calling a prediction API.
container_hash <- hash("/artifact/ep_model.rda")
stopifnot(container_hash == Sys.getenv("EP_CONTAINER_SHA256"))
contents <- new.env(parent = emptyenv())
objects <- load("/artifact/ep_model.rda", envir = contents)
stopifnot(identical(objects, "ep_model"), identical(ls(contents), "ep_model"))
payload <- contents$ep_model
stopifnot(is.raw(payload), is.null(attributes(payload)),
          length(payload) > 0L, length(payload) <= 16L * 1024L * 1024L,
          identical(payload, fastrmodels::ep_model))
scratch <- tempfile("ep-equality-", tmpdir = "/tmp")
writeBin(payload, scratch)
payload_hash <- hash(scratch)
stopifnot(file.info(scratch)$size == length(payload), payload_hash == Sys.getenv("EP_RAW_SHA256"))

installed <- installed.packages()[, c("Package", "Version", "License"), drop = FALSE]
installed <- installed[order(installed[, "Package"]), , drop = FALSE]
required <- sort(unique(c("nflfastR", unlist(tools::package_dependencies("nflfastR",
  db = installed.packages(), which = c("Depends", "Imports", "LinkingTo"), recursive = TRUE)))))
stopifnot(!"tcltk" %in% required)
shared <- sort(unlist(lapply(.libPaths(), function(p)
  list.files(p, pattern = "\\.so$", recursive = TRUE, full.names = TRUE))))
linked <- character()
unresolved_optional <- list()
for (path in shared) {
  deps <- system2("ldd", shQuote(path), stdout = TRUE)
  stopifnot(is.null(attr(deps, "status")))
  missing <- trimws(sub(" => not found.*", "", deps[grepl("=> not found", deps)]))
  if (length(missing)) {
    # The pinned headless base ships tcltk.so without GUI runtimes. Never hide a
    # missing reference dependency or install unrelated GUI packages to pass.
    stopifnot(path == system.file("libs", "tcltk.so", package = "tcltk"),
              identical(sort(missing), c("libtcl8.6.so", "libtk8.6.so")))
    unresolved_optional[[length(unresolved_optional) + 1L]] <- list(path = path, libraries = missing)
  }
  linked <- c(linked, sub(".*=> (/[^ ]+).*", "\\1", deps[grepl("=> /", deps)]))
}
identify <- function(paths) lapply(sort(unique(paths)), function(p) list(path = p, sha256 = hash(p)))
format <- "${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Status}\n"
out <- system2("dpkg-query", c("-W", shQuote(paste0("-f=", format))), stdout = TRUE)
stopifnot(is.null(attr(out, "status")))
rows <- Filter(function(x) length(x) == 4L && x[4L] == "installed", strsplit(out, "\t", fixed = TRUE))
packages <- lapply(rows, function(x)
  list(package = sub(":.*", "", x[1L]), version = x[2L], architecture = x[3L]))
packages <- packages[order(vapply(packages, `[[`, "", "package"))]
stopifnot(identical(packages, native$after))
record <- list(
  status = "reference_installed_ep_bytes_verified", r_version = as.character(getRversion()),
  platform = R.version$platform, compiler = system2("g++", "-dumpfullversion", stdout = TRUE),
  libc = system2("ldd", "--version", stdout = TRUE)[1L],
  r_external_libraries = as.list(extSoftVersion()),
  source_lock_sha256 = hash(file.path(root, "ep_runtime.lock.json")),
  native_lock_sha256 = hash(file.path(root, "ep_native.lock.json")),
  dockerfile_sha256 = hash(file.path(root, "Dockerfile")),
  installed_r_packages = unname(lapply(seq_len(nrow(installed)), function(i) as.list(installed[i, ]))),
  installed_native_packages = packages, shared_libraries = identify(shared),
  linked_native_libraries = identify(linked), xgboost_config = xgboost::xgb.get.config(),
  required_r_packages = required, unresolved_optional_libraries = unresolved_optional,
  native_installation = list(added = native$added, upgraded = native$upgraded,
    removed = native$removed, before_count = length(native$before), after_count = length(native$after),
    installation_record_sha256 = hash(file.path(root, "native-installation.json"))),
  container_sha256 = container_hash, raw_bytes = length(payload), raw_sha256 = payload_hash,
  installed_package_equality_verified = TRUE, full_reference_installed = TRUE,
  persisted_raw_export = FALSE, model_executed = FALSE, prediction_capture_available = FALSE,
  predictive_validation = FALSE)
cat(jsonlite::toJSON(record, auto_unbox = TRUE, pretty = TRUE, digits = NA), "\n", sep = "")
