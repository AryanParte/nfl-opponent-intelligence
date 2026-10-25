# Read-only container inspection, not XGBoost inference or a prediction capture.
# Invoke through validation.ep_probe after Python verifies the pinned Git bytes.
options(warn = 2)
stopifnot(as.character(getRversion()) == "4.6.1")

sha256_file <- function(path) {
  result <- system2("sha256sum", shQuote(path), stdout = TRUE)
  stopifnot(is.null(attr(result, "status")), length(result) == 1L)
  digest <- substr(result, 1L, 64L)
  stopifnot(grepl("^[0-9a-f]{64}$", digest))
  digest
}

container_hash <- sha256_file("/artifact/ep_model.rda")
stopifnot(container_hash == Sys.getenv("EP_CONTAINER_SHA256"))
contents <- new.env(parent = emptyenv())
objects <- load("/artifact/ep_model.rda", envir = contents)
stopifnot(identical(objects, "ep_model"), identical(ls(contents), "ep_model"))
payload <- contents$ep_model
stopifnot(is.raw(payload), is.null(attributes(payload)),
          length(payload) > 0L, length(payload) <= 16L * 1024L * 1024L)

# Scratch bytes are removed with the disposable container, never published as
# the final payload. Installed-package equality still needs a provisioned stack.
scratch <- tempfile("ep-inspection-", tmpdir = "/tmp")
writeBin(payload, scratch)
payload_hash <- sha256_file(scratch)
stopifnot(file.info(scratch)$size == length(payload))
prefix <- paste(sprintf("%02x", as.integer(head(payload, 16L))), collapse = "")
platform <- R.version$platform
stopifnot(grepl("^[a-zA-Z0-9_-]+$", platform))
cat(sprintf(paste0(
  '{"status":"raw_object_inspected","r_version":"4.6.1",',
  '"platform":"%s","container_sha256":"%s",',
  '"object_name":"ep_model","object_type":"raw","raw_bytes":%d,',
  '"raw_sha256":"%s","prefix_hex":"%s",',
  '"installed_package_equality_verified":false,"model_executed":false}\n'),
  platform, container_hash, length(payload), payload_hash, prefix))
