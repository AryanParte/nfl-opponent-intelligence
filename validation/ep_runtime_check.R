# Verify only the built native dependency stage. Never load an NFL model here.
options(warn = 2)
stopifnot(as.character(getRversion()) == "4.6.1",
          as.character(packageVersion("xgboost")) == "3.4.2.1",
          as.character(packageVersion("jsonlite")) == "2.0.0",
          as.character(packageVersion("data.table")) == "1.18.6.1")
invisible(xgboost::xgb.set.config(nthread = 1L))
stopifnot(xgboost::xgb.get.config()$nthread == 1L)
hash <- function(path) {
  output <- system2("sha256sum", shQuote(path), stdout = TRUE)
  stopifnot(is.null(attr(output, "status")))
  substr(output, 1L, 64L)
}
installed <- installed.packages()[, c("Package", "Version", "License"), drop = FALSE]
installed <- installed[order(installed[, "Package"]), , drop = FALSE]
library_path <- system.file("libs", "xgboost.so", package = "xgboost")
deps <- system2("ldd", shQuote(library_path), stdout = TRUE)
stopifnot(is.null(attr(deps, "status")), !any(grepl("not found", deps)))
paths <- sub(".*=> (/[^ ]+).*", "\\1", deps[grepl("=> /", deps)])
native <- lapply(sort(unique(paths)), function(p) list(path = p, sha256 = hash(p)))
record <- list(
  status = "xgboost_native_stage_verified_reference_incomplete",
  r_version = as.character(getRversion()), platform = R.version$platform,
  compiler = system2("g++", "-dumpfullversion", stdout = TRUE),
  libc = system2("ldd", "--version", stdout = TRUE)[1L],
  installed_packages = unname(lapply(seq_len(nrow(installed)), function(i)
    as.list(installed[i, ]))),
  xgboost_library_sha256 = hash(library_path), linked_native_libraries = native,
  xgboost_config = xgboost::xgb.get.config(),
  curl_headers_present = any(file.exists(c("/usr/include/curl/curl.h",
    "/usr/include/aarch64-linux-gnu/curl/curl.h", "/usr/local/include/curl/curl.h"))),
  pkg_config_present = nzchar(Sys.which("pkg-config")),
  nflfastr_installed = requireNamespace("nflfastR", quietly = TRUE),
  full_reference_ready = FALSE, model_executed = FALSE, predictive_validation = FALSE)
cat(jsonlite::toJSON(record, auto_unbox = TRUE, pretty = TRUE, digits = NA), "\n", sep = "")
