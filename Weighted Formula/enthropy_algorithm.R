# ==============================================================================
# Configuration
# ==============================================================================
values_path   <- "final_metrics_value.csv"
metrics <- c("CiD","CMod","SCF","SMAD","DCCMD")

# ---- Cap and Variance switches -----------------------------------------------
use_variance_gate <- FALSE   # FALSE => original formula
use_cap           <- FALSE  # FALSE => original formula
cap_default       <- 0.25   # only used if use_cap == TRUE


# ==============================================================================
# HELPERS
# ==============================================================================

# Safe correlation calculation
safe_cor <- function(x, y) {
  if (sd(x) == 0 || sd(y) == 0) return(0)
  cor(x, y, method = "spearman")
}

normalize_prob <- function(v, zero_ok = FALSE) {
  # Handle non-finite values: Na/NAN types
  v[!is.finite(v)] <- 0
  v[v < 0] <- 0
  
  # Calculate sum for normalization
  s <- sum(v, na.rm = TRUE)
  
  # Handle edge cases: all values are zero or negative
  if (s <= 0) {
    if (zero_ok) return(rep(0, length(v)))
    return(rep(1/length(v), length(v)))
  }
  v / s
}

blend_with_ranking <- function(computed, scores, alpha = 0.75, cap = NA) {
  # Input validation
  stopifnot(length(computed) == length(scores),
            all(names(computed) == names(scores)))
  
  # Normalize probabilities
  comp <- normalize_prob(computed)
  
  # Clean and normalize scores
  # Handle non-finite values: Na/NAN types
  sc <- pmax(0, ifelse(is.finite(scores), scores, 0))
  w_score <- normalize_prob(sc, zero_ok = TRUE)
  
  # Blend the two distributions using alpha weighting
  final <- alpha * comp + (1 - alpha) * w_score
  
  # Normalize the blended result
  final <- normalize_prob(final)
  
  # Apply cap constraint (optional)
  if (is.finite(cap) && cap < 1) {
    final <- project_capped_simplex(final, cap = cap)
  }
  
  final
}

project_capped_simplex <- function(v, cap = 0.25, tol = 1e-10) {
  m <- length(v)
  stopifnot(m * cap + 1e-12 >= 1)  # feasibility check, it must add to one
  
  # Handle non-finite values: Na/NAN types
  v[!is.finite(v)] <- 0
  
  # Define the constraint function: sum(clamp(v - lambda)) = 1
  f <- function(lambda) sum(pmin(pmax(v - lambda, 0), cap)) - 1
  
  # Find brackets where f changes sign
  lo <- min(v) - cap
  hi <- max(v)
  
  # Expand brackets if needed (with safety limits)
  for (i in 1:50) { if (f(lo) <= 0) break; lo <- lo - 1 }
  for (i in 1:50) { if (f(hi) >= 0) break; hi <- hi + 1 }
  
  # Solve for lambda using uniroot
  tryCatch({
    lambda <- uniroot(f, c(lo, hi), tol = tol)$root
    w <- pmin(pmax(v - lambda, 0), cap)
    return(w / sum(w))  # Normalize (sum should be 1, but ensure it)
  }, error = function(e) {
    # Fallback: uniform distribution respecting caps
    rep(min(cap, 1/m), m)
  })
}


# ==============================================================================
# Algorithm
# ==============================================================================
# 1. load the data --------------------------------------------------------------
df <- read.csv(values_path, stringsAsFactors = FALSE)

# 2. choose the metrics --------------------------------------------------------
stopifnot(all(metrics %in% names(df)))
X <- df[, metrics, drop = TRUE]
n <- nrow(X)

# orientation (all TRUE here) --------------------------------------------------
maximize <- c(CiD=TRUE, CMod=TRUE, SCF=TRUE, SMAD=TRUE, DCCMD=TRUE)

# 3. monotone (CDF) normalisation + orientation --------------------------------
norm_cdf <- function(x) ecdf(x)(x)
S <- as.data.frame(lapply(as.data.frame(X), norm_cdf))
for (m in metrics) if (!maximize[m]) S[[m]] <- 1 - S[[m]]

# 4. entropy weights -----------------------------------------------------------
P   <- as.data.frame(lapply(S, function(col) col / sum(col)))
eps <- 1e-12
e   <- sapply(P, function(pj) -sum(pj * log(pj + eps)) / log(n))
d   <- pmax(0, 1 - e)
names(d) <- names(S)
w_ent <- normalize_prob(d)

# 5. robust aggregate & rank ---------------------------------------------------
F_unw <- rowMeans(S)
R_unw <- rank(-F_unw, ties.method = "average")

# 6. dependency/diversity weights ----------------------------------------------
spearman_rho <- function(x, y) {
  if (sd(x) < 1e-9) return(1)
  r <- suppressWarnings(cor(rank(x), y, method = "spearman"))
  if (is.na(r)) 0 else abs(r)
}
rho <- sapply(S, function(col) spearman_rho(col, R_unw))
w_dep_raw <- 1 - rho
w_dep <- if (all(w_dep_raw <= 1e-12)) rep(1/length(rho), length(rho)) else normalize_prob(w_dep_raw)
names(w_dep) <- names(rho)

# 6a.variance gate (optional) --------------------------------------------------
safe_var_over_mean2 <- function(col) {
  mu <- mean(col)
  if (abs(mu) < 1e-12) return(0)
  var(col) / (mu^2)
}
w_var <- sapply(S, safe_var_over_mean2)
w_var <- if (sum(w_var) == 0) rep(1/length(w_var), length(w_var)) else normalize_prob(w_var)
names(w_var) <- names(S)

# 7. combined weights  ---------------------------------------------------------
if (!use_variance_gate) {
  w_var_eff <- rep(1, length(w_dep))
  names(w_var_eff) <- names(w_dep)
} else {
  w_var_eff <- w_var
}
w_comb <- w_ent * w_dep * w_var_eff
w_comb <- normalize_prob(w_comb)
w_comb <- w_comb[metrics]

# 8. blend with human scores + cap (optional) ----------------------------------
user_scores   <- setNames(rep(0, length(metrics)), metrics)
alpha_default <- 0.75

final_w_uncapped <- blend_with_ranking(w_comb, user_scores, alpha = alpha_default, cap = NA)
final_w          <- blend_with_ranking(
  w_comb, user_scores,
  alpha = alpha_default,
  cap   = if (use_cap) cap_default else NA
)

# 9. results -------------------------------------------------------------------
weights <- data.frame(
  metric     = metrics,
  entropy    = round(w_ent[metrics], 3),
  dependency = round(w_dep[metrics], 3),
  variance   = round(w_var[metrics], 3),
  combined   = round(w_comb[metrics], 3),
  blended    = round(final_w_uncapped[metrics], 3),
  final_cap  = round(final_w[metrics], 3),
  row.names  = NULL,
  stringsAsFactors = FALSE
)
print(weights)