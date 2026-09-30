check_valid_data <- function() {
  stopifnot(tb.checks::check_data(data.frame(x = 1:3), "x"))
}

check_invalid_data <- function() {
  stopifnot(raises_error(tb.checks::check_data(NULL, "x")))
  stopifnot(raises_error(tb.checks::check_data(data.frame(x = "a"), "x")))
  stopifnot(raises_error(tb.checks::check_data(data.frame(x = c(1, NA)), "x")))
  stopifnot(raises_error(tb.checks::check_data(data.frame(x = numeric()), "x")))
  stopifnot(raises_error(tb.checks::check_data(data.frame(x = 1), "missing")))
}

raises_error <- function(expression) {
  inherits(tryCatch(force(expression), error = identity), "error")
}

check_valid_data()
check_invalid_data()
