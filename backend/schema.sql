-- PostgreSQL schema for the Tingathe AI CV Screening System
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE users (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), email text UNIQUE NOT NULL, password_hash text NOT NULL, full_name text NOT NULL, phone text,
  role text NOT NULL CHECK (role IN ('applicant','director')), is_active boolean NOT NULL DEFAULT true, preferred_language text NOT NULL DEFAULT 'en', created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE applicant_profiles (user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, district text, consent_at timestamptz);
CREATE TABLE categories (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text UNIQUE NOT NULL, description text);
CREATE TABLE vacancies (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), category_id uuid REFERENCES categories(id), title text NOT NULL, summary text, description text, employment_type text, image_key text,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','open','closed','archived')), closing_date date, created_by uuid REFERENCES users(id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE vacancy_criteria (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vacancy_id uuid NOT NULL REFERENCES vacancies(id) ON DELETE CASCADE,
  criterion_type text NOT NULL CHECK (criterion_type IN ('qualification','skill','experience','keyword')), label text NOT NULL, required_value text, weight numeric NOT NULL CHECK (weight >= 0), is_mandatory boolean NOT NULL DEFAULT false);
CREATE TABLE applications (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vacancy_id uuid NOT NULL REFERENCES vacancies(id), applicant_id uuid NOT NULL REFERENCES users(id),
  status text NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted','processing','screened','needs_review','decided')), cover_note text, submitted_at timestamptz NOT NULL DEFAULT now(), UNIQUE (vacancy_id, applicant_id));
CREATE TABLE documents (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), application_id uuid NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  doc_type text NOT NULL CHECK (doc_type IN ('cv','qualification','other')), original_name text NOT NULL, storage_path text NOT NULL, mime_type text, size_bytes integer, sha256 text, uploaded_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE extraction_runs (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  method text NOT NULL CHECK (method IN ('pdf_text','docx','ocr')), status text NOT NULL CHECK (status IN ('ok','partial','failed')), text_content text, confidence numeric, warnings jsonb, finished_at timestamptz);
CREATE TABLE candidate_profiles (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), application_id uuid UNIQUE NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  total_experience_months integer, extraction_status text CHECK (extraction_status IN ('ok','needs_review')), built_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE profile_items (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), profile_id uuid NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
  item_type text NOT NULL CHECK (item_type IN ('education','skill','qualification','experience')), value text NOT NULL, institution text, start_date date, end_date date,
  source_document_id uuid REFERENCES documents(id), source_snippet text, confidence numeric);
CREATE TABLE screening_results (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), application_id uuid NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  total_score numeric NOT NULL, rank integer, scoring_version text, run_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE criterion_scores (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), result_id uuid NOT NULL REFERENCES screening_results(id) ON DELETE CASCADE,
  criterion_id uuid NOT NULL REFERENCES vacancy_criteria(id), matched boolean NOT NULL, score numeric NOT NULL, evidence_item_id uuid REFERENCES profile_items(id), explanation text);
CREATE TABLE decisions (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), application_id uuid NOT NULL REFERENCES applications(id) ON DELETE CASCADE, decided_by uuid NOT NULL REFERENCES users(id),
  decision text NOT NULL CHECK (decision IN ('shortlist','hold','not_shortlisted')), note text, decided_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE report_exports (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vacancy_id uuid NOT NULL REFERENCES vacancies(id), generated_by uuid NOT NULL REFERENCES users(id),
  format text NOT NULL CHECK (format IN ('pdf','csv')), file_path text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE audit_logs (id bigserial PRIMARY KEY, actor_id uuid REFERENCES users(id), action text NOT NULL, entity_type text, entity_id uuid, metadata jsonb, created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX ON applications (vacancy_id); CREATE INDEX ON documents (application_id); CREATE INDEX ON screening_results (application_id); CREATE INDEX ON criterion_scores (result_id);
