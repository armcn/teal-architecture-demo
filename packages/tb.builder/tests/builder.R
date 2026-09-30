stopifnot(inherits(tb.builder::run_app(), "shiny.appobj"))
destination <- tempfile()
err <- tryCatch(tb.builder::export_app(destination, release_dir = tempdir()), error = identity)
stopifnot(inherits(err, "error"), !dir.exists(destination))
