CREATE TYPE scope_type AS ENUM ('archdiocese', 'vicariate', 'parish', 'community');

CREATE TABLE archdioceses (
    id          uuid PRIMARY KEY,
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  uuid,
    updated_at  timestamptz,
    updated_by  uuid,
    deleted_at  timestamptz
);

CREATE UNIQUE INDEX archdioceses_name_unique
    ON archdioceses (name)
    WHERE deleted_at IS NULL;

CREATE TABLE vicariates (
    id              uuid PRIMARY KEY,
    archdiocese_id  uuid NOT NULL,
    name            text NOT NULL,
    sector          text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    created_by      uuid,
    updated_at      timestamptz,
    updated_by      uuid,
    deleted_at      timestamptz,
    CONSTRAINT vicariates_archdiocese_fk
        FOREIGN KEY (archdiocese_id) REFERENCES archdioceses (id)
);

CREATE UNIQUE INDEX vicariates_name_unique
    ON vicariates (archdiocese_id, name)
    WHERE deleted_at IS NULL;

CREATE TABLE parishes (
    id            uuid PRIMARY KEY,
    vicariate_id  uuid NOT NULL,
    name          text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    created_by    uuid,
    updated_at    timestamptz,
    updated_by    uuid,
    deleted_at    timestamptz,
    CONSTRAINT parishes_vicariate_fk
        FOREIGN KEY (vicariate_id) REFERENCES vicariates (id)
);

CREATE UNIQUE INDEX parishes_name_unique
    ON parishes (vicariate_id, name)
    WHERE deleted_at IS NULL;

CREATE TABLE communities (
    id          uuid PRIMARY KEY,
    parish_id   uuid NOT NULL,
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  uuid,
    updated_at  timestamptz,
    updated_by  uuid,
    deleted_at  timestamptz,
    CONSTRAINT communities_parish_fk
        FOREIGN KEY (parish_id) REFERENCES parishes (id)
);

CREATE UNIQUE INDEX communities_name_unique
    ON communities (parish_id, name)
    WHERE deleted_at IS NULL;

ALTER TABLE archdioceses ENABLE ROW LEVEL SECURITY;
ALTER TABLE vicariates ENABLE ROW LEVEL SECURITY;
ALTER TABLE parishes ENABLE ROW LEVEL SECURITY;
ALTER TABLE communities ENABLE ROW LEVEL SECURITY;
