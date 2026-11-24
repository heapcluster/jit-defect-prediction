-- JIT 缺陷预测 建表脚本（MySQL 8.0）
-- 口径来源：docs/database/{commit,model,commit_feature,model_figure,prediction}.md
-- 共 12 张表：现有 5 张 + 重构新增 7 张（user/user_config/job/algorithm/model_artifact/dataset/dataset_commit）；
-- SZZ 真标签直接落在 commit_feature.is_bug_inducing / labeled_at

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
	model_version VARCHAR(64) NULL,
	feature_version VARCHAR(32) NULL,
	PRIMARY KEY (commit_hash, model_name),
	FOREIGN KEY(commit_hash) REFERENCES commit (commit_hash),
	FOREIGN KEY(model_name) REFERENCES model (model_name),
	INDEX ix_prediction_model_risk (model_name, risk_score)
);

-- ── 重构新增 7 表（契约见 docs/database/{user,user_config,job,algorithm,model_artifact,dataset}.md）──
-- 本轮只落 DDL 与预置行；迁移脚本与「空库/旧库/重复执行」三冒烟押代码波次。
-- 一期不动现有 5 表主键；数据集多版本（dataset_commit 加 feature_version 进主键）押二期。

CREATE TABLE IF NOT EXISTS `user` (
	user_id VARCHAR(36) NOT NULL,
	display_name VARCHAR(64) NOT NULL,
	role VARCHAR(16) NOT NULL DEFAULT 'member',
	status VARCHAR(16) NOT NULL DEFAULT 'active',
	created_at DATETIME NOT NULL,
	PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS user_config (
	user_id VARCHAR(36) NOT NULL,
	config_key VARCHAR(64) NOT NULL,
	value_json TEXT NOT NULL,
	value_type VARCHAR(16) NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (user_id, config_key),
	FOREIGN KEY(user_id) REFERENCES `user` (user_id)
);

CREATE TABLE IF NOT EXISTS job (
	job_id VARCHAR(36) NOT NULL,
	kind VARCHAR(16) NOT NULL,
	status VARCHAR(16) NOT NULL DEFAULT 'queued',
	params_json TEXT,
	total INT NOT NULL DEFAULT 0,
	done INT NOT NULL DEFAULT 0,
	current_item VARCHAR(64),
	started_at DATETIME,
	finished_at DATETIME,
	error_log TEXT,
	retry_count INT NOT NULL DEFAULT 0,
	output_ref_json TEXT,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (job_id),
	INDEX ix_job_kind_status (kind, status)
);

CREATE TABLE IF NOT EXISTS algorithm (
	line VARCHAR(16) NOT NULL,
	algo VARCHAR(64) NOT NULL,
	family VARCHAR(32) NOT NULL,
	hyperparams_json TEXT NOT NULL,
	enabled TINYINT(1) NOT NULL DEFAULT 1,
	description VARCHAR(255),
	PRIMARY KEY (line, algo)
);

CREATE TABLE IF NOT EXISTS model_artifact (
	artifact_id VARCHAR(36) NOT NULL,
	model_name VARCHAR(64) NOT NULL,
	line VARCHAR(16) NOT NULL,
	algo VARCHAR(64),
	version_key VARCHAR(64) NOT NULL DEFAULT '',
	weight_path VARCHAR(255) NOT NULL,
	checksum_sha256 CHAR(64) NOT NULL,
	size_bytes BIGINT NOT NULL DEFAULT 0,
	feature_version VARCHAR(32),
	train_job_id VARCHAR(36),
	status VARCHAR(16) NOT NULL DEFAULT 'available',
	trained_at DATETIME,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (artifact_id),
	UNIQUE KEY uk_artifact_model (model_name),
	FOREIGN KEY(model_name) REFERENCES model (model_name),
	FOREIGN KEY(train_job_id) REFERENCES job (job_id),
	INDEX ix_artifact_line (line)
);

CREATE TABLE IF NOT EXISTS dataset (
	dataset_id VARCHAR(36) NOT NULL,
	name VARCHAR(128) NOT NULL,
	repo_source VARCHAR(255) NOT NULL,
	branch VARCHAR(128),
	head_hash CHAR(40),
	time_start DATETIME,
	time_end DATETIME,
	mode VARCHAR(16) NOT NULL DEFAULT 'full',
	sample_count INT NOT NULL DEFAULT 0,
	pos_count INT NOT NULL DEFAULT 0,
	neg_count INT NOT NULL DEFAULT 0,
	status VARCHAR(16) NOT NULL DEFAULT 'collecting',
	job_id VARCHAR(36),
	created_at DATETIME NOT NULL,
	PRIMARY KEY (dataset_id),
	FOREIGN KEY(job_id) REFERENCES job (job_id)
);

CREATE TABLE IF NOT EXISTS dataset_commit (
	dataset_id VARCHAR(36) NOT NULL,
	commit_hash CHAR(40) NOT NULL,
	PRIMARY KEY (dataset_id, commit_hash),
	FOREIGN KEY(dataset_id) REFERENCES dataset (dataset_id),
	FOREIGN KEY(commit_hash) REFERENCES commit (commit_hash)
);

-- 预置全局配置归属行（docs/database/user.md）；INSERT IGNORE 保证重复执行幂等。
INSERT IGNORE INTO `user` (user_id, display_name, role, status, created_at)
VALUES ('global', '全局默认', 'system', 'active', UTC_TIMESTAMP());
