CREATE TYPE document_type AS ENUM ('cedula', 'passport', 'refugee_id');

CREATE TYPE sex AS ENUM ('male', 'female');

CREATE TYPE role_name AS ENUM (
    'archdiocese_admin',
    'vicariate_admin',
    'parish_admin',
    'community_admin',
    'catechist',
    'representative',
    'catechumen'
);

CREATE TABLE persons (
    id                uuid PRIMARY KEY,
    document_type     document_type NOT NULL,
    document_number   text NOT NULL,
    first_names       text NOT NULL,
    paternal_surname  text NOT NULL,
    maternal_surname  text,
    birth_date        date NOT NULL,
    sex               sex NOT NULL,
    phone             text,
    contact_email     text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    created_by        uuid,
    updated_at        timestamptz,
    updated_by        uuid,
    deleted_at        timestamptz,
    CONSTRAINT persons_document_unique UNIQUE (document_type, document_number)
);

CREATE INDEX persons_by_surnames
    ON persons (paternal_surname, maternal_surname)
    WHERE deleted_at IS NULL;

CREATE TABLE user_accounts (
    id                    uuid PRIMARY KEY,
    person_id             uuid NOT NULL,
    external_user_id      uuid NOT NULL,
    is_active             boolean NOT NULL,
    must_change_password  boolean NOT NULL,
    last_login_at         timestamptz,
    created_at            timestamptz NOT NULL DEFAULT now(),
    created_by            uuid,
    updated_at            timestamptz,
    updated_by            uuid,
    deleted_at            timestamptz,
    CONSTRAINT user_accounts_person_fk
        FOREIGN KEY (person_id) REFERENCES persons (id),
    CONSTRAINT user_accounts_external_user_unique UNIQUE (external_user_id),
    CONSTRAINT user_accounts_created_by_fk
        FOREIGN KEY (created_by) REFERENCES user_accounts (id),
    CONSTRAINT user_accounts_updated_by_fk
        FOREIGN KEY (updated_by) REFERENCES user_accounts (id)
);

CREATE UNIQUE INDEX user_accounts_one_per_person
    ON user_accounts (person_id)
    WHERE deleted_at IS NULL;

CREATE TABLE role_assignments (
    id               uuid PRIMARY KEY,
    user_account_id  uuid NOT NULL,
    role             role_name NOT NULL,
    scope_type       scope_type NOT NULL,
    scope_id         uuid NOT NULL,
    revoked_at       timestamptz,
    revoked_by       uuid,
    created_at       timestamptz NOT NULL DEFAULT now(),
    created_by       uuid,
    updated_at       timestamptz,
    updated_by       uuid,
    deleted_at       timestamptz,
    CONSTRAINT role_assignments_account_fk
        FOREIGN KEY (user_account_id) REFERENCES user_accounts (id),
    CONSTRAINT role_assignments_revoked_by_fk
        FOREIGN KEY (revoked_by) REFERENCES user_accounts (id),
    CONSTRAINT role_assignments_created_by_fk
        FOREIGN KEY (created_by) REFERENCES user_accounts (id),
    CONSTRAINT role_assignments_updated_by_fk
        FOREIGN KEY (updated_by) REFERENCES user_accounts (id)
);

CREATE UNIQUE INDEX role_assignments_active_unique
    ON role_assignments (user_account_id, role, scope_type, scope_id)
    WHERE revoked_at IS NULL AND deleted_at IS NULL;

CREATE INDEX role_assignments_by_account
    ON role_assignments (user_account_id)
    WHERE revoked_at IS NULL AND deleted_at IS NULL;

CREATE INDEX role_assignments_by_scope
    ON role_assignments (scope_type, scope_id)
    WHERE revoked_at IS NULL AND deleted_at IS NULL;

ALTER TABLE persons
    ADD CONSTRAINT persons_created_by_fk FOREIGN KEY (created_by) REFERENCES user_accounts (id),
    ADD CONSTRAINT persons_updated_by_fk FOREIGN KEY (updated_by) REFERENCES user_accounts (id);

ALTER TABLE archdioceses
    ADD CONSTRAINT archdioceses_created_by_fk FOREIGN KEY (created_by) REFERENCES user_accounts (id),
    ADD CONSTRAINT archdioceses_updated_by_fk FOREIGN KEY (updated_by) REFERENCES user_accounts (id);

ALTER TABLE vicariates
    ADD CONSTRAINT vicariates_created_by_fk FOREIGN KEY (created_by) REFERENCES user_accounts (id),
    ADD CONSTRAINT vicariates_updated_by_fk FOREIGN KEY (updated_by) REFERENCES user_accounts (id);

ALTER TABLE parishes
    ADD CONSTRAINT parishes_created_by_fk FOREIGN KEY (created_by) REFERENCES user_accounts (id),
    ADD CONSTRAINT parishes_updated_by_fk FOREIGN KEY (updated_by) REFERENCES user_accounts (id);

ALTER TABLE communities
    ADD CONSTRAINT communities_created_by_fk FOREIGN KEY (created_by) REFERENCES user_accounts (id),
    ADD CONSTRAINT communities_updated_by_fk FOREIGN KEY (updated_by) REFERENCES user_accounts (id);

ALTER TABLE persons ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_assignments ENABLE ROW LEVEL SECURITY;
