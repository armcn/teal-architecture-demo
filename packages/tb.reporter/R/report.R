report_text <- function(values) {
  sprintf("Observations: %d | Mean: %.2f", length(values), mean(values))
}
