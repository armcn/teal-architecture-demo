args <- commandArgs(TRUE)
stopifnot(length(args) == 1L)
tools::write_PACKAGES(args[[1]], type = "source", latestOnly = FALSE)
