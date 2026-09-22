ALTER TABLE communities
    DROP CONSTRAINT communities_created_by_fk,
    DROP CONSTRAINT communities_updated_by_fk;

ALTER TABLE parishes
    DROP CONSTRAINT parishes_created_by_fk,
    DROP CONSTRAINT parishes_updated_by_fk;

ALTER TABLE vicariates
    DROP CONSTRAINT vicariates_created_by_fk,
    DROP CONSTRAINT vicariates_updated_by_fk;

ALTER TABLE archdioceses
    DROP CONSTRAINT archdioceses_created_by_fk,
    DROP CONSTRAINT archdioceses_updated_by_fk;

ALTER TABLE persons
    DROP CONSTRAINT persons_created_by_fk,
    DROP CONSTRAINT persons_updated_by_fk;

DROP TABLE role_assignments;
DROP TABLE user_accounts;
DROP TABLE persons;
DROP TYPE role_name;
DROP TYPE sex;
DROP TYPE document_type;
