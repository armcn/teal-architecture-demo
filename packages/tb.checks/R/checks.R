# Validation is pure: success returns TRUE; invalid inputs raise clear errors.
check_data <- function(data, column) {
  require_data_frame(data)
  require_existing_column(data, column)
  require_numeric_values(data[[column]])
  invisible(TRUE)
}

require_data_frame <- function(data) {
  if (!is.data.frame(data)) {
    stop("Expected a data frame", call. = FALSE)
  }
}

require_existing_column <- function(data, column) {
  is_single_name <- is.character(column) && length(column) == 1L
  if (!is_single_name || is.na(column) || !column %in% names(data)) {
    stop("Choose an existing column", call. = FALSE)
  }
}

require_numeric_values <- function(values) {
  if (!is.numeric(values) || !length(values) || any(!is.finite(values))) {
    stop("Column must contain finite numeric values", call. = FALSE)
  }
}
