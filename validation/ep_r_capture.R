# Repository-only offline EP reference, not an NFL dataset or production adapter.
# Inputs contain full synthetic states, NEVER expected feature/prediction vectors.
# See NOTICE.md and docs/EP_R_CAPTURE.md for attribution and instrumentation.
options(warn = 2)
hash <- function(path) {
  out <- system2("sha256sum", shQuote(path), stdout = TRUE)
  stopifnot(is.null(attr(out, "status")), length(out) == 1L)
  substr(out, 1L, 64L)
}
write_json <- function(x, path) jsonlite::write_json(
  x, path, auto_unbox = TRUE, pretty = TRUE, digits = NA)

main <- function() {
  input <- jsonlite::fromJSON("/input.json", simplifyVector = FALSE)
  states <- input$states
  stopifnot(length(states) == 25L, as.character(getRversion()) == "4.6.1",
            as.character(packageVersion("xgboost")) == "3.4.2.1",
            as.character(packageVersion("nflfastR")) == "6.0.0",
            as.character(packageVersion("fastrmodels")) == "2.1.0")
  invisible(xgboost::xgb.set.config(nthread = 1L))
  stopifnot(xgboost::xgb.get.config()$nthread == 1L)
  stopifnot(hash("/artifact/ep_model.rda") == input$container_sha256,
            hash("/artifact/manifest.json") == input$artifact_manifest_sha256)
  contents <- new.env(parent = emptyenv())
  objects <- load("/artifact/ep_model.rda", envir = contents)
  stopifnot(identical(objects, "ep_model"), identical(ls(contents), "ep_model"))
  payload <- contents$ep_model
  stopifnot(is.raw(payload), is.null(attributes(payload)), length(payload) == 9737490L,
            identical(payload, fastrmodels::ep_model))
  writeBin(payload, "/output/ep_model.ubj")
  stopifnot(hash("/output/ep_model.ubj") == input$model_sha256)

  data <- do.call(rbind, lapply(states, function(x) as.data.frame(x$state)))
  ids <- vapply(states, `[[`, "", "id")
  # Standalone nflfastR consumes half time. This explicit adapter does not use
  # the Python oracle or its expected vectors; upstream computes all other fields.
  data$half_seconds_remaining <- data$quarter_seconds_remaining +
    ifelse(data$qtr %in% c(1L, 3L), 900L, 0L)

  assign(".ep_trace", new.env(parent = emptyenv()), envir = .GlobalEnv)
  trace_state <- get(".ep_trace", envir = .GlobalEnv)
  trace_state$payload <- payload
  trace_state$matrices <- list()
  trace_state$loads <- 0L
  on.exit(rm(".ep_trace", envir = .GlobalEnv), add = TRUE)
  # Observe the *actual* argument at the native prediction boundary. Never
  # replace a model, feature selector, prediction, or numerical result.
  invisible(trace("predict.xgb.Booster", where = asNamespace("xgboost"), print = FALSE,
    tracer = quote({
      s <- get(".ep_trace", envir = .GlobalEnv)
      stopifnot(is.matrix(newdata), is.numeric(newdata), all(is.finite(newdata)))
      s$matrices[[length(s$matrices) + 1L]] <- newdata
    })))
  prediction_traced <- TRUE
  on.exit(if (prediction_traced)
    untrace("predict.xgb.Booster", where = asNamespace("xgboost")), add = TRUE)
  invisible(trace("xgb.load.raw", where = asNamespace("xgboost"), print = FALSE,
    tracer = quote({
      s <- get(".ep_trace", envir = .GlobalEnv)
      stopifnot(identical(buffer, s$payload))
      s$loads <- s$loads + 1L
    })))
  loader_traced <- TRUE
  on.exit(if (loader_traced)
    untrace("xgb.load.raw", where = asNamespace("xgboost")), add = TRUE)
  classes <- c("td_prob", "opp_td_prob", "fg_prob", "opp_fg_prob",
               "safety_prob", "opp_safety_prob", "no_score_prob")
  rows <- function(result, matrix, names) {
    stopifnot(nrow(result) == length(names), nrow(matrix) == length(names),
              identical(colnames(result)[seq_len(7L)], classes))
    lapply(seq_along(names), function(i) list(id = names[i],
      features = unname(matrix[i, ]),
      probabilities = unname(unlist(result[i, classes])), ep = result$ep[i]))
  }
  batch <- nflfastR::calculate_expected_points(data)
  stopifnot(length(trace_state$matrices) == 1L, trace_state$loads == 1L)
  batch_matrix <- trace_state$matrices[[1L]]
  single <- lapply(seq_len(nrow(data)), function(i) {
    result <- nflfastR::calculate_expected_points(data[i, , drop = FALSE])
    stopifnot(length(trace_state$matrices) == i + 1L, trace_state$loads == i + 1L,
              identical(colnames(trace_state$matrices[[i + 1L]]), colnames(batch_matrix)))
    rows(result, trace_state$matrices[[i + 1L]], ids[i])[[1L]]
  })
  # Removing observation must not change output. Use strict equality here;
  # the separate protocol applies the predeclared numerical tolerances.
  untrace("predict.xgb.Booster", where = asNamespace("xgboost"))
  prediction_traced <- FALSE
  untrace("xgb.load.raw", where = asNamespace("xgboost"))
  loader_traced <- FALSE
  replay <- nflfastR::calculate_expected_points(data)
  stopifnot(identical(batch, replay))
  record <- list(protocol_version = 1L, probability_origin = "model_capture",
    fixture_sha256 = input$fixture_sha256, source_commits = input$source_commits,
    model_sha256 = input$model_sha256, artifact_manifest_sha256 = input$artifact_manifest_sha256,
    runtime = list(language = "R", version = as.character(getRversion()),
      xgboost_version = as.character(packageVersion("xgboost")), platform = R.version$platform,
      environment_sha256 = input$environment_sha256, runner_sha256 = hash("/runner.R")),
    feature_order = colnames(batch_matrix), class_order = classes,
    batch = rows(batch, batch_matrix, ids), single = single)
  write_json(record, "/output/capture.json")
  write_json(list(status = "upstream_reference_captured", traced_predictions = 26L,
    verified_raw_loads = trace_state$loads, untraced_batch_identical = TRUE,
    input_sha256 = hash("/input.json"), model_sha256 = hash("/output/ep_model.ubj"),
    model_bytes = length(payload), installed_package_equality_verified = TRUE,
    xgboost_config = xgboost::xgb.get.config()), "/output/observation.json")
}
main()
