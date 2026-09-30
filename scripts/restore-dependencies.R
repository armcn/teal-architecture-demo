# Install the source lockfile's external dependencies for package checks.
source("scripts/bootstrap.R")

restore_build_dependencies <- function() {
  bootstrap_renv()
  options(repos = c(CRAN = "https://cloud.r-project.org"), timeout = 300)
  Sys.setenv(
    RENV_CONFIG_AUTOLOADER_ENABLED = "FALSE",
    RENV_CONFIG_CACHE_ENABLED = "FALSE"
  )
  library <- file.path(getwd(), ".work", "dependencies")
  dir.create(library, recursive = TRUE, showWarnings = FALSE)
  renv::restore(
    project = getwd(), lockfile = "renv.lock",
    library = library, prompt = FALSE
  )
}

restore_build_dependencies()
