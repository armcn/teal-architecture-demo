report_text <- function(values) {
  if (!length(values)) return("Observations: 0 | Mean: NA | Range: NA")
  sprintf("Observations: %d | Mean: %.2f | Range: %.2f to %.2f",
          length(values), mean(values), min(values), max(values))
}
