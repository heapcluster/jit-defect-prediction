CREATE TABLE IF NOT EXISTS commit (
    id BIGINT NOT NULL AUTO_INCREMENT,
    repo_name VARCHAR(64) NOT NULL,
    commit_hash CHAR(40) NOT NULL,
    author_name VARCHAR(128) NOT NULL,
    author_email VARCHAR(128),
    committed_at DATETIME NOT NULL,
    message TEXT NOT NULL,
    parent_hash CHAR(40),
    PRIMARY KEY (id),
    UNIQUE (commit_hash),
    INDEX ix_commit_committed_at (committed_at)
);

CREATE TABLE IF NOT EXISTS commit_feature (
    commit_hash CHAR(40) NOT NULL,
    committed_at DATETIME NOT NULL,
    feature_version VARCHAR(32) NOT NULL,
    ns DECIMAL(20, 10) NOT NULL,
    nd DECIMAL(20, 10) NOT NULL,
    nf DECIMAL(20, 10) NOT NULL,
    entropy DECIMAL(20, 10) NOT NULL,
    la DECIMAL(20, 10) NOT NULL,
    ld DECIMAL(20, 10) NOT NULL,
    lt DECIMAL(20, 10) NOT NULL,
    fix TINYINT(1) NOT NULL,
    ndev DECIMAL(20, 10) NOT NULL,
    age DECIMAL(20, 10) NOT NULL,
    nuc DECIMAL(20, 10) NOT NULL,
    exp DECIMAL(20, 10) NOT NULL,
    rexp DECIMAL(20, 10) NOT NULL,
    sexp DECIMAL(20, 10) NOT NULL,
    PRIMARY KEY (commit_hash)
);

CREATE TABLE IF NOT EXISTS commit_label (
    id BIGINT NOT NULL AUTO_INCREMENT,
    commit_hash CHAR(40) NOT NULL,
    is_bug_inducing TINYINT(1) NOT NULL,
    label_method VARCHAR(32) NOT NULL,
    bug_fix_hash CHAR(40),
    labeled_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_label_hash_method UNIQUE (commit_hash, label_method),
    INDEX ix_commit_label_commit_hash (commit_hash)
);

CREATE TABLE IF NOT EXISTS prediction (
    id BIGINT NOT NULL AUTO_INCREMENT,
    commit_hash CHAR(40) NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    risk_score DECIMAL(6, 5) NOT NULL,
    predicted_at DATETIME NOT NULL,
    feature_version VARCHAR(32) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_prediction_hash_model UNIQUE (commit_hash, model_name),
    INDEX ix_prediction_commit_hash (commit_hash)
);
