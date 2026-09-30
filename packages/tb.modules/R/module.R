# Compute the result independently of Shiny's reactive state.
summarize_data <- function(data, column) {
  tb.checks::check_data(data, column)
  values <- data[[column]]
  list(
    n = length(values),
    mean = mean(values),
    report = tb.reporter::report_text(values)
  )
}

module_ui <- function(id) {
  namespace <- shiny::NS(id)
  shiny::tagList(
    shiny::h3("Generated app preview"),
    shiny::textOutput(namespace("summary"))
  )
}

module_server <- function(id, column) {
  shiny::moduleServer(id, function(input, output, session) {
    result <- shiny::reactive(summarize_data(datasets::mtcars, column()))
    output$summary <- shiny::renderText(result()$report)
    result
  })
}

run_example <- function(column = "mpg") {
  tb.checks::check_data(datasets::mtcars, column)
  shiny::shinyApp(
    ui = example_ui(),
    server = example_server(column)
  )
}

example_ui <- function() {
  shiny::fluidPage(
    shiny::h2("Exported example app"),
    module_ui("example")
  )
}

example_server <- function(column) {
  force(column)
  function(input, output, session) {
    module_server("example", shiny::reactive(column))
  }
}
