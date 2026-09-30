check_summary <- function() {
  summary <- tb.modules::summarize_data(data.frame(x = c(2, 4)), "x")
  stopifnot(summary$n == 2, summary$mean == 3)
}

check_standalone_app <- function() {
  stopifnot(inherits(tb.modules::run_example(), "shiny.appobj"))
}

check_reactive_module <- function() {
  shiny::testServer(
    tb.modules::module_server,
    args = list(column = shiny::reactive("mpg")),
    { stopifnot(result()$n == nrow(datasets::mtcars)) }
  )
}

check_summary()
check_standalone_app()
check_reactive_module()
