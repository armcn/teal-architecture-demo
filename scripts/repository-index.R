# Create the index files used by install.packages() and renv.
main <- function() {
  arguments <- commandArgs(TRUE)
  stopifnot(length(arguments) == 1L)
  tools::write_PACKAGES(
    arguments[[1]], type = "source", latestOnly = FALSE
  )
}

main()
