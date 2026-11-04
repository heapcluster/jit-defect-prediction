-- JIT 缺陷预测 建表脚本（MySQL 8.0）
-- 口径来源：docs/database/{commit,model,commit_feature,model_figure,prediction}.md
-- 共 5 张表；SZZ 真标签直接落在 commit_feature.is_bug_inducing / labeled_at

CREATE TABLE IF NOT EXISTS commit (
	commit_hash CHAR(40) NOT NULL,
	repo_name VARCHAR(64) NOT NULL,
	author_name VARCHAR(128) NOT NULL,
	author_email VARCHAR(128),
	committed_at DATETIME NOT NULL,
	message TEXT NOT NULL,
	parent_hash CHAR(40),
	PRIMARY KEY (commit_hash),
	INDEX ix_commit_committed_at (committed_at)
);

CREATE TABLE IF NOT EXISTS model (
	model_name VARCHAR(64) NOT NULL,
	line VARCHAR(16) NOT NULL DEFAULT 'expert',
	algo VARCHAR(64),
	version_key VARCHAR(64) NOT NULL DEFAULT '',
	trained_at DATETIME,
	feature_version VARCHAR(32),
	PRIMARY KEY (model_name),
	INDEX ix_model_line (line)
);

CREATE TABLE IF NOT EXISTS commit_feature (
	commit_hash CHAR(40) NOT NULL,
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
	is_test TINYINT(1) NOT NULL DEFAULT 0,
	is_bug_inducing TINYINT(1),
	labeled_at DATETIME,
	PRIMARY KEY (commit_hash),
	FOREIGN KEY(commit_hash) REFERENCES commit (commit_hash),
	INDEX ix_commit_feature_is_test (is_test)
);

CREATE TABLE IF NOT EXISTS model_figure (
	model_name VARCHAR(64) NOT NULL,
	figure_type VARCHAR(32) NOT NULL,
	title VARCHAR(128) NOT NULL,
	file_path VARCHAR(255) NOT NULL,
	generated_at DATETIME NOT NULL,
	PRIMARY KEY (model_name, figure_type),
	FOREIGN KEY(model_name) REFERENCES model (model_name)
);

CREATE TABLE IF NOT EXISTS prediction (
	commit_hash CHAR(40) NOT NULL,
	model_name VARCHAR(64) NOT NULL,
	risk_score DECIMAL(6, 5) NOT NULL,
	predicted_at DATETIME NOT NULL,
	PRIMARY KEY (commit_hash, model_name),
	FOREIGN KEY(commit_hash) REFERENCES commit (commit_hash),
	FOREIGN KEY(model_name) REFERENCES model (model_name),
	INDEX ix_prediction_model_risk (model_name, risk_score)
);
