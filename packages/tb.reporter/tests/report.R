check_report_values <- function() {
  stopifnot(identical(
    tb.reporter::report_text(c(2, 4)),
    "Observations: 2 | Mean: 3.00 | Range: 2.00 to 4.00"
  ))
  stopifnot(identical(
    tb.reporter::report_text(c(-2, -2)),
    "Observations: 2 | Mean: -2.00 | Range: -2.00 to -2.00"
  ))
}

check_empty_report <- function() {
  previous_options <- options(warn = 2)
  on.exit(options(previous_options), add = TRUE)
  stopifnot(identical(
    tb.reporter::report_text(numeric(0)),
    "Observations: 0 | Mean: NA | Range: NA"
  ))
}

check_report_values()
check_empty_report()
