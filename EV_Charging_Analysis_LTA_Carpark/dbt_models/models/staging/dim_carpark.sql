select *
from {{ source('datamall', 'hdb_carpark') }}