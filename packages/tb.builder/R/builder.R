# The public entry points describe the app and export operations.
run_app <- function(release_dir = getwd()) {
  release_id <- read_release_id(release_dir)
  shiny::shinyApp(
    ui = builder_ui(release_id),
    server = builder_server(release_dir)
  )
}

export_app <- function(path, column = "mpg", release_dir = getwd()) {
  tb.checks::check_data(datasets::mtcars, column)
  release_files <- export_release_files()
  validate_export_destination(path, release_dir, release_files)
  copy_release_files(path, release_dir, release_files)
  writeLines(exported_app_code(column), file.path(path, "app.R"))
  writeLines(export_instructions(), file.path(path, "README.txt"))
  invisible(normalizePath(path))
}

# Pure descriptions: UI, generated code, and export contents.
builder_ui <- function(release_id) {
  shiny::fluidPage(
    shiny::h2("Teal architecture example"),
    shiny::p(paste("Release:", release_id)),
    shiny::selectInput("column", "Choose a variable", names(datasets::mtcars)),
    tb.modules::module_ui("preview"),
    shiny::downloadButton("export", "Download app and dependency lock")
  )
}

export_release_files <- function() {
  c("renv.lock", "release.json", "restore.R", "bootstrap.R")
}

exported_app_code <- function(column) {
  quoted_column <- encodeString(column, quote = '"')
  sprintf("tb.modules::run_example(%s)", quoted_column)
}

export_instructions <- function() {
  c(
    "1. Run Rscript restore.R",
    "2. Run Rscript -e 'shiny::runApp()'",
    "This export retains the original release lockfile."
  )
}

# Shiny callbacks and filesystem actions stay at the boundaries.
builder_server <- function(release_dir) {
  force(release_dir)
  function(input, output, session) {
    tb.modules::module_server("preview", shiny::reactive(input$column))
    output$export <- shiny::downloadHandler(
      filename = function() "example-app.zip",
      content = function(file) {
        write_export_zip(file, input$column, release_dir)
      }
    )
  }
}

read_release_id <- function(release_dir) {
  release_file <- file.path(release_dir, "release.json")
  if (!file.exists(release_file)) {
    return("local development")
  }
  jsonlite::read_json(release_file)$snapshot
}

validate_export_destination <- function(path, release_dir, release_files) {
  if (file.exists(path)) {
    stop("Export destination already exists", call. = FALSE)
  }
  if (!all(file.exists(file.path(release_dir, release_files)))) {
    stop("Export requires a prepared release directory", call. = FALSE)
  }
}

copy_release_files <- function(path, release_dir, release_files) {
  dir.create(path, recursive = TRUE)
  copied <- file.copy(file.path(release_dir, release_files), path)
  if (!all(copied)) {
    stop("Export copy failed", call. = FALSE)
  }
}

write_export_zip <- function(destination, column, release_dir) {
  directory <- tempfile("export-")
  dir.create(directory)
  on.exit(unlink(directory, recursive = TRUE), add = TRUE)
  export_app(file.path(directory, "example-app"), column, release_dir)

  previous_directory <- setwd(directory)
  on.exit(setwd(previous_directory), add = TRUE, after = FALSE)
  files <- list.files("example-app", recursive = TRUE, full.names = TRUE)
  utils::zip(destination, files)
}
