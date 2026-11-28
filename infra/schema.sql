-- JIT 缺陷预测 建表脚本（MySQL 8.0）
-- 与 docs/数据库/ 对齐：15 张表；业务数据按 owner_user_id 归属用户。
-- 允许受控冗余（不追求严格 BCNF）：dataset_commit 保存提交元数据与特征快照，
-- evaluation / prediction 保存展示用冗余字段；冗余只服务历史可读性，不作为新的写入真源。
-- commit 使用内部 commit_id 作主键，(repo_name, commit_hash) 唯一：
-- 同一哈希出现在不同仓库时，历史类特征（exp / rexp / sexp / ndev）按仓库计算，必须分两行。
-- 主键 ID 统一为「类型前缀 + 32 位小写十六进制」，总长不超过 CHAR(36)：
-- u_ / ds_ / job_ / eva_ / art_ / fig_ / cmt_；commit_hash 统一小写。
-- 账号由初始化脚本创建，本脚本不预置任何用户。

CREATE TABLE IF NOT EXISTS `user` (
	user_id CHAR(36) NOT NULL,
	username VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
	password VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
	display_name VARCHAR(64) NOT NULL,
	status VARCHAR(16) NOT NULL DEFAULT 'active',
	created_at DATETIME NOT NULL,
	last_login_at DATETIME NULL,
	PRIMARY KEY (user_id),
	UNIQUE KEY uk_user_username (username)
);

CREATE TABLE IF NOT EXISTS user_session (
	session_id CHAR(64) NOT NULL,
	user_id CHAR(36) NOT NULL,
	created_at DATETIME NOT NULL,
	last_seen_at DATETIME NOT NULL,
	expires_at DATETIME NOT NULL,
	PRIMARY KEY (session_id),
	CONSTRAINT fk_user_session_user FOREIGN KEY (user_id) REFERENCES `user` (user_id) ON DELETE CASCADE,
	INDEX ix_user_session_user (user_id),
	INDEX ix_user_session_expires (expires_at)
);

CREATE TABLE IF NOT EXISTS user_config (
	user_id CHAR(36) NOT NULL,
	config_key VARCHAR(64) NOT NULL,
	value_json TEXT NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (user_id, config_key),
	CONSTRAINT fk_user_config_user FOREIGN KEY (user_id) REFERENCES `user` (user_id)
);

CREATE TABLE IF NOT EXISTS user_page_state (
	user_id CHAR(36) NOT NULL,
	page VARCHAR(16) NOT NULL,
	state_json MEDIUMTEXT NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (user_id, page),
	CONSTRAINT fk_page_state_user FOREIGN KEY (user_id) REFERENCES `user` (user_id)
);

CREATE TABLE IF NOT EXISTS commit (
	commit_id CHAR(36) NOT NULL,
	commit_hash CHAR(40) NOT NULL,
	repo_name VARCHAR(128) NOT NULL,
	author_name VARCHAR(128) NOT NULL,
	author_email VARCHAR(128),
	committed_at DATETIME NOT NULL,
	message TEXT NOT NULL,
	parent_hash CHAR(40),
	PRIMARY KEY (commit_id),
	UNIQUE KEY uk_commit_repo_hash (repo_name, commit_hash),
	INDEX ix_commit_hash (commit_hash),
	INDEX ix_commit_committed_at (committed_at)
);

CREATE TABLE IF NOT EXISTS commit_feature (
	commit_id CHAR(36) NOT NULL,
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
	is_bug_inducing TINYINT(1),
	labeled_at DATETIME,
	PRIMARY KEY (commit_id, feature_version),
	CONSTRAINT fk_commit_feature_commit FOREIGN KEY (commit_id) REFERENCES commit (commit_id)
);

CREATE TABLE IF NOT EXISTS job (
	job_id CHAR(36) NOT NULL,
	owner_user_id CHAR(36) NOT NULL,
	kind VARCHAR(16) NOT NULL,
	status VARCHAR(16) NOT NULL DEFAULT 'queued',
	params_json TEXT,
	total INT NOT NULL DEFAULT 0,
	done INT NOT NULL DEFAULT 0,
	current_stage VARCHAR(64),
	output_ref_json TEXT,
	error_message TEXT,
	created_at DATETIME NOT NULL,
	started_at DATETIME,
	finished_at DATETIME,
	PRIMARY KEY (job_id),
	CONSTRAINT fk_job_user FOREIGN KEY (owner_user_id) REFERENCES `user` (user_id),
	INDEX ix_job_owner_status (owner_user_id, status),
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

CREATE TABLE IF NOT EXISTS dataset (
	dataset_id CHAR(36) NOT NULL,
	owner_user_id CHAR(36) NOT NULL,
	name VARCHAR(128) NOT NULL,
	line VARCHAR(16) NOT NULL DEFAULT 'expert',
	source_type VARCHAR(16) NOT NULL DEFAULT 'git_repo',
	parent_dataset_id CHAR(36) NULL,
	repo_url VARCHAR(512),
	repo_name VARCHAR(128),
	platform VARCHAR(16),
	branch VARCHAR(128),
	head_hash CHAR(40),
	time_start DATETIME,
	time_end DATETIME,
	sample_count INT NOT NULL DEFAULT 0,
	pos_count INT NOT NULL DEFAULT 0,
	neg_count INT NOT NULL DEFAULT 0,
	feature_version VARCHAR(32),
	dedupe_key CHAR(64),
	status VARCHAR(16) NOT NULL DEFAULT 'ready',
	job_id CHAR(36),
	manifest_path VARCHAR(512),
	created_at DATETIME NOT NULL,
	PRIMARY KEY (dataset_id),
	CONSTRAINT fk_dataset_owner FOREIGN KEY (owner_user_id) REFERENCES `user` (user_id),
	CONSTRAINT fk_dataset_parent FOREIGN KEY (parent_dataset_id) REFERENCES dataset (dataset_id) ON DELETE SET NULL,
	CONSTRAINT fk_dataset_job FOREIGN KEY (job_id) REFERENCES job (job_id),
	INDEX ix_dataset_owner (owner_user_id, created_at),
	INDEX ix_dataset_parent (parent_dataset_id),
	UNIQUE KEY uk_dataset_dedupe (owner_user_id, dedupe_key)
);

CREATE TABLE IF NOT EXISTS dataset_commit (
	dataset_id CHAR(36) NOT NULL,
	commit_id CHAR(36) NOT NULL,
	commit_hash CHAR(40) NOT NULL,
	repo_url VARCHAR(512),
	branch VARCHAR(128),
	author_name VARCHAR(128),
	author_email VARCHAR(128),
	committed_at DATETIME,
	message TEXT,
	parent_hash CHAR(40),
	is_bug_inducing TINYINT(1),
	label_method VARCHAR(32),
	fix_commit_hash CHAR(40),
	feature_json JSON,
	row_no INT NOT NULL DEFAULT 0,
	PRIMARY KEY (dataset_id, commit_hash),
	CONSTRAINT fk_dataset_commit_dataset FOREIGN KEY (dataset_id) REFERENCES dataset (dataset_id) ON DELETE CASCADE,
	CONSTRAINT fk_dataset_commit_commit FOREIGN KEY (commit_id) REFERENCES commit (commit_id)
);

CREATE TABLE IF NOT EXISTS model (
	model_name VARCHAR(64) NOT NULL,
	owner_user_id CHAR(36) NOT NULL,
	line VARCHAR(16) NOT NULL DEFAULT 'expert',
	algo VARCHAR(64),
	version_key VARCHAR(64) NOT NULL DEFAULT '',
	trained_at DATETIME,
	feature_version VARCHAR(32),
	train_dataset_id CHAR(36),
	test_dataset_id CHAR(36),
	params_json TEXT,
	metrics_json TEXT,
	PRIMARY KEY (model_name),
	CONSTRAINT fk_model_owner FOREIGN KEY (owner_user_id) REFERENCES `user` (user_id),
	CONSTRAINT fk_model_train_dataset FOREIGN KEY (train_dataset_id) REFERENCES dataset (dataset_id) ON DELETE SET NULL,
	CONSTRAINT fk_model_test_dataset FOREIGN KEY (test_dataset_id) REFERENCES dataset (dataset_id) ON DELETE SET NULL,
	INDEX ix_model_owner (owner_user_id),
	INDEX ix_model_line (line)
);

CREATE TABLE IF NOT EXISTS model_artifact (
	artifact_id CHAR(36) NOT NULL,
	model_name VARCHAR(64) NOT NULL,
	line VARCHAR(16) NOT NULL,
	algo VARCHAR(64),
	framework VARCHAR(16) NOT NULL DEFAULT 'sklearn',
	format VARCHAR(8) NOT NULL DEFAULT 'pkl',
	version_key VARCHAR(64) NOT NULL DEFAULT '',
	weight_path VARCHAR(255) NOT NULL,
	checksum_sha256 CHAR(64) NOT NULL,
	size_bytes BIGINT NOT NULL DEFAULT 0,
	feature_version VARCHAR(32),
	train_job_id CHAR(36),
	status VARCHAR(16) NOT NULL DEFAULT 'available',
	trained_at DATETIME,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (artifact_id),
	UNIQUE KEY uk_artifact_model (model_name),
	CONSTRAINT fk_artifact_model FOREIGN KEY (model_name) REFERENCES model (model_name) ON DELETE CASCADE,
	CONSTRAINT fk_artifact_job FOREIGN KEY (train_job_id) REFERENCES job (job_id),
	INDEX ix_artifact_line (line)
);

CREATE TABLE IF NOT EXISTS evaluation (
	evaluation_id CHAR(36) NOT NULL,
	owner_user_id CHAR(36) NOT NULL,
	name VARCHAR(128) NOT NULL,
	source_kind VARCHAR(16) NOT NULL,
	source_label VARCHAR(255) NOT NULL,
	dataset_id CHAR(36),
	model_name VARCHAR(64),
	model_label VARCHAR(128),
	threshold DECIMAL(4, 3) NOT NULL DEFAULT 0.500,
	metrics_json JSON NOT NULL,
	sample_count INT NOT NULL DEFAULT 0,
	pos_count INT NOT NULL DEFAULT 0,
	neg_count INT NOT NULL DEFAULT 0,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (evaluation_id),
	CONSTRAINT fk_evaluation_user FOREIGN KEY (owner_user_id) REFERENCES `user` (user_id) ON DELETE CASCADE,
	CONSTRAINT fk_evaluation_dataset FOREIGN KEY (dataset_id) REFERENCES dataset (dataset_id) ON DELETE SET NULL,
	CONSTRAINT fk_evaluation_model FOREIGN KEY (model_name) REFERENCES model (model_name) ON DELETE SET NULL,
	UNIQUE KEY uq_evaluation_user_name (owner_user_id, name),
	INDEX ix_evaluation_user_created (owner_user_id, created_at)
);

CREATE TABLE IF NOT EXISTS evaluation_figure (
	figure_id CHAR(36) NOT NULL,
	evaluation_id CHAR(36) NOT NULL,
	figure_type VARCHAR(16) NOT NULL,
	file_path VARCHAR(512) NOT NULL,
	sha256 CHAR(64) NOT NULL,
	width INT,
	height INT,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (figure_id),
	CONSTRAINT fk_evaluation_figure FOREIGN KEY (evaluation_id) REFERENCES evaluation (evaluation_id) ON DELETE CASCADE,
	UNIQUE KEY uq_evaluation_figure_type (evaluation_id, figure_type),
	INDEX ix_evaluation_figure_evaluation (evaluation_id)
);

CREATE TABLE IF NOT EXISTS prediction (
	dataset_id CHAR(36) NOT NULL,
	commit_hash CHAR(40) NOT NULL,
	commit_id CHAR(36),
	model_name VARCHAR(64),
	model_label VARCHAR(128),
	risk_score DECIMAL(6, 5) NOT NULL,
	predicted_label TINYINT NOT NULL,
	threshold DECIMAL(4, 3) NOT NULL DEFAULT 0.500,
	actual_label TINYINT,
	feature_version VARCHAR(32),
	predicted_at DATETIME NOT NULL,
	PRIMARY KEY (dataset_id, commit_hash),
	CONSTRAINT fk_prediction_dataset FOREIGN KEY (dataset_id) REFERENCES dataset (dataset_id) ON DELETE CASCADE,
	CONSTRAINT fk_prediction_commit FOREIGN KEY (commit_id) REFERENCES commit (commit_id) ON DELETE SET NULL,
	CONSTRAINT fk_prediction_model FOREIGN KEY (model_name) REFERENCES model (model_name) ON DELETE SET NULL,
	INDEX ix_prediction_model (model_name),
	INDEX ix_prediction_dataset (dataset_id)
);
