result <- tb.modules::summarize_data(data.frame(x = c(2, 4)), "x")
stopifnot(result$n == 2, result$mean == 3)
stopifnot(inherits(tb.modules::run_example(), "shiny.appobj"))
shiny::testServer(tb.modules::module_server, args = list(column = shiny::reactive("mpg")), {
  stopifnot(result()$n == nrow(datasets::mtcars))
})
