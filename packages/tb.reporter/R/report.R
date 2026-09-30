report_text <- function(values) {
  sprintf("Observations: %d | Mean: %.2f | Range: %.2f to %.2f",
          length(values), mean(values), min(values), max(values))
}
