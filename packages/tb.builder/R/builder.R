export_app <- function(path, column = "mpg", release_dir = getwd()) {
  tb.checks::check_data(datasets::mtcars, column)
  if (file.exists(path)) stop("Export destination already exists", call. = FALSE)
  required <- c("renv.lock", "release.json", "restore.R", "bootstrap.R")
  if (!all(file.exists(file.path(release_dir, required)))) {
    stop("Export requires a prepared release directory", call. = FALSE)
  }
  dir.create(path, recursive = TRUE)
  if (!all(file.copy(file.path(release_dir, required), path))) stop("Export copy failed")
  writeLines(sprintf("tb.modules::run_example(%s)", encodeString(column, quote = '"')),
             file.path(path, "app.R"))
  writeLines(c("1. Run Rscript restore.R", "2. Run Rscript -e 'shiny::runApp()'",
               "This export retains the original release lockfile."), file.path(path, "README.txt"))
  invisible(normalizePath(path))
}

run_app <- function(release_dir = getwd()) {
  release_file <- file.path(release_dir, "release.json")
  release_id <- if (file.exists(release_file)) jsonlite::read_json(release_file)$snapshot else "local development"
  shiny::shinyApp(
    shiny::fluidPage(
      shiny::h2("Teal architecture example"),
      shiny::p(paste("Release:", release_id)),
      shiny::selectInput("column", "Choose a variable", names(datasets::mtcars)),
      tb.modules::module_ui("preview"),
      shiny::downloadButton("export", "Download app and dependency lock")
    ),
    function(input, output, session) {
      tb.modules::module_server("preview", shiny::reactive(input$column))
      output$export <- shiny::downloadHandler(
        filename = function() "example-app.zip",
        content = function(file) {
          root <- tempfile("export-")
          dir.create(root)
          on.exit(unlink(root, recursive = TRUE), add = TRUE)
          export_app(file.path(root, "example-app"), input$column, release_dir)
          previous <- setwd(root)
          on.exit(setwd(previous), add = TRUE)
          utils::zip(file, list.files("example-app", recursive = TRUE, full.names = TRUE))
        }
      )
    }
  )
}
