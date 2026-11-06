CREATE TABLE "directives"(
    "id" SERIAL NOT NULL,
    "selector" TEXT NOT NULL,
    "directive_type" VARCHAR(255) NOT NULL,
    "directive_data" TEXT NULL,
    "applies_to" TEXT NOT NULL DEFAULT '*',
    "active" BOOLEAN NOT NULL
);
ALTER TABLE
    "directives" ADD PRIMARY KEY("id");
CREATE INDEX "directives_selector_index" ON
    "directives"("selector");
CREATE INDEX "directives_active_index" ON
    "directives"("active");


CREATE TABLE "users"(
    "id" SERIAL NOT NULL,
    "username" VARCHAR(255) NOT NULL,
    "password" CHAR(64) NOT NULL,
    "super_admin" BOOLEAN NOT NULL DEFAULT FALSE
);
ALTER TABLE
    "users" ADD PRIMARY KEY("id");
CREATE INDEX "users_username_index" ON
    "users"("username");


CREATE TABLE "audit_log"(
    "id" SERIAL NOT NULL,
    "user" INTEGER NOT NULL,
    "directive" INTEGER NOT NULL,
    "action" VARCHAR(255) NOT NULL,
    "note" TEXT NULL
);
ALTER TABLE
    "audit_log" ADD PRIMARY KEY("id");
ALTER TABLE
    "audit_log" ADD CONSTRAINT "audit_log_user_foreign" FOREIGN KEY("user") REFERENCES "users"("id");
ALTER TABLE
    "audit_log" ADD CONSTRAINT "audit_log_directive_foreign" FOREIGN KEY("directive") REFERENCES "directives"("id");
