check_data <- function(data, column) {
  if (!is.data.frame(data)) stop("Expected a data frame", call. = FALSE)
  if (length(column) != 1L || !is.character(column) || is.na(column) || !column %in% names(data)) {
    stop("Choose an existing column", call. = FALSE)
  }
  values <- data[[column]]
  if (!is.numeric(values) || !length(values) || any(!is.finite(values))) {
    stop("Column must contain finite numeric values", call. = FALSE)
  }
  invisible(TRUE)
}
