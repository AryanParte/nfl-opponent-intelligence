# Verify every Debian archive before an entirely offline container-only install.
options(warn = 2)
lock <- jsonlite::fromJSON("/opt/ep-runtime/ep_native.lock.json", simplifyVector = FALSE)
hash <- function(path) {
  out <- system2("sha256sum", shQuote(path), stdout = TRUE)
  stopifnot(is.null(attr(out, "status")))
  substr(out, 1L, 64L)
}
inventory <- function() {
  format <- "${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Status}\n"
  out <- system2("dpkg-query", c("-W", shQuote(paste0("-f=", format))), stdout = TRUE)
  stopifnot(is.null(attr(out, "status")))
  rows <- strsplit(out, "\t", fixed = TRUE)
  rows <- Filter(function(x) length(x) == 4L && x[4L] == "installed", rows)
  packages <- lapply(rows, function(x)
    list(package = sub(":.*", "", x[1L]), version = x[2L], architecture = x[3L]))
  names(packages) <- vapply(packages, `[[`, "", "package")
  stopifnot(!anyDuplicated(names(packages)))
  packages[order(names(packages))]
}
before <- inventory()
paths <- vapply(lock$packages, function(p) {
  path <- file.path("/opt/ep-runtime", p$filename)
  stopifnot(!p$package %in% names(before), file.info(path)$size == p$size_bytes,
            hash(path) == p$sha256)
  fields <- lapply(c("Package", "Version", "Architecture"), function(field)
    system2("dpkg-deb", c("--field", shQuote(path), field), stdout = TRUE))
  stopifnot(identical(fields, list(p$package, p$version, p$architecture)))
  path
}, "")
stopifnot(system2("dpkg", c("--install", shQuote(paths))) == 0L)
after <- inventory()
stopifnot(identical(after[names(before)], before),
          setequal(setdiff(names(after), names(before)), vapply(lock$packages, `[[`, "", "package")))
for (p in lock$packages) {
  stopifnot(identical(after[[p$package]], p[c("package", "version", "architecture")]),
            hash(p$copyright_path) == p$copyright_sha256)
}
writeLines(jsonlite::toJSON(list(status = "native_dependencies_verified",
  native_lock_sha256 = hash("/opt/ep-runtime/ep_native.lock.json"),
  before = unname(before), after = unname(after), upgraded = 0L, removed = 0L,
  added = vapply(lock$packages, `[[`, "", "package")),
  auto_unbox = TRUE, pretty = TRUE), "/opt/ep-runtime/native-installation.json")
