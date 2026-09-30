check_builder_app <- function() {
  stopifnot(inherits(tb.builder::run_app(), "shiny.appobj"))
}

check_incomplete_release_is_rejected <- function() {
  destination <- tempfile()
  error <- tryCatch(
    tb.builder::export_app(destination, release_dir = tempdir()),
    error = identity
  )
  stopifnot(inherits(error, "error"), !dir.exists(destination))
}

check_builder_app()
check_incomplete_release_is_rejected()
