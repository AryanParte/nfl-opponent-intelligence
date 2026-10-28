# Inspect only verified native .deb sources inside the pinned isolated container.
# Output is metadata/notice text, not an installation or model execution.
options(warn = 2)
lock <- jsonlite::fromJSON("/validation/ep_native.lock.json", simplifyVector = FALSE)
hash <- function(path) {
  out <- system2("sha256sum", shQuote(path), stdout = TRUE)
  stopifnot(is.null(attr(out, "status")))
  substr(out, 1L, 64L)
}
records <- lapply(lock$packages, function(p) {
  path <- file.path("/native/archives", p$filename)
  stopifnot(file.info(path)$size == p$size_bytes, hash(path) == p$sha256)
  fields <- lapply(c("Package", "Version", "Architecture"), function(field)
    system2("dpkg-deb", c("--field", shQuote(path), field), stdout = TRUE))
  stopifnot(identical(fields, list(p$package, p$version, p$architecture)))
  directory <- tempfile("ep-deb-")
  dir.create(directory)
  on.exit(unlink(directory, recursive = TRUE), add = TRUE)
  stopifnot(system2("dpkg-deb", c("--extract", shQuote(path), shQuote(directory))) == 0L)
  notice <- file.path(directory, "usr/share/doc", p$package, "copyright")
  stopifnot(file.exists(notice), hash(notice) == p$copyright_sha256)
  list(package = p$package, version = p$version, architecture = p$architecture,
       sha256 = hash(path), copyright_sha256 = hash(notice),
       copyright_text = paste(readLines(notice, warn = FALSE), collapse = "\n"))
})
stopifnot(hash("/usr/share/keyrings/ubuntu-archive-keyring.gpg") == lock$ubuntu_keyring_sha256)
releases <- lapply(lock$signed_releases, function(record) {
  path <- file.path("/native/lists", record$file)
  stopifnot(hash(path) == record$sha256)
  output <- system2("gpgv", c("--status-fd", "1", "--keyring",
    "/usr/share/keyrings/ubuntu-archive-keyring.gpg", shQuote(path)), stdout = TRUE)
  stopifnot(is.null(attr(output, "status")),
            identical(output[grepl("^\\[GNUPG:\\] VALIDSIG ", output)], record$valid_signature))
  list(file = basename(path), sha256 = hash(path),
       valid_signature = output[grepl("^\\[GNUPG:\\] VALIDSIG ", output)])
})
stopifnot(length(releases) == 3L)
notices <- list()
for (p in records) notices[[p$copyright_sha256]] <- p$copyright_text
records <- lapply(records, function(p) { p$copyright_text <- NULL; p })
cat(jsonlite::toJSON(list(packages = records, signed_releases = releases, notices = notices),
  auto_unbox = TRUE, pretty = TRUE), "\n", sep = "")
