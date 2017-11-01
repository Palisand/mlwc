BEGIN TRANSACTION;

ALTER TABLE meet RENAME TO meet_old;

CREATE TABLE meet (
  id INTEGER NOT NULL,
  sanction_number VARCHAR(20) NOT NULL,
  name VARCHAR NOT NULL,
  date DATE NOT NULL,
  city VARCHAR,
  state VARCHAR,
  PRIMARY KEY (id)
);

INSERT INTO meet (id, sanction_number, name, date, city, state)
  SELECT id, sanction_number, name, date, city, state
  FROM meet_old;

DROP TABLE meet_old;

COMMIT;