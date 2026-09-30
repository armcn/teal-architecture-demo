summarize_data <- function(data, column) {
  tb.checks::check_data(data, column)
  list(n = length(data[[column]]), mean = mean(data[[column]]),
       report = tb.reporter::report_text(data[[column]]))
}

module_ui <- function(id) {
  ns <- shiny::NS(id)
  shiny::tagList(shiny::h3("Generated app preview"), shiny::textOutput(ns("summary")))
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
    shiny::fluidPage(shiny::h2("Exported example app"), module_ui("example")),
    function(input, output, session) module_server("example", shiny::reactive(column))
  )
}
