# Offline installation only. All archives/notices are retained in the local image.
options(repos = NULL, warn = 2)
lock <- jsonlite::fromJSON("/opt/ep-runtime/ep_runtime.lock.json", simplifyVector = FALSE)
stopifnot(as.character(getRversion()) == lock$r_version)
for (record in lock$packages) {
  name <- record$package
  if (name %in% c("jsonlite", "data.table", "xgboost")) {
    stopifnot(as.character(packageVersion(name)) == record$version)
    next
  }
  path <- file.path("/opt/ep-runtime", record$filename)
  status <- system2(file.path(R.home("bin"), "R"), c("CMD", "INSTALL", shQuote(path)))
  stopifnot(status == 0L, as.character(packageVersion(name)) == record$version)
}
stopifnot(as.character(packageVersion("nflfastR")) == "6.0.0",
          as.character(packageVersion("fastrmodels")) == "2.1.0")
