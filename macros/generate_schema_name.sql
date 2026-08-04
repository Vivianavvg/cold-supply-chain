{#
    The 'dev' target is this project's only long-lived warehouse (doubles as
    "prod" for portfolio purposes) - it keeps the literal bronze/silver/gold
    dataset names already in use there. Every other target (e.g. 'ci') gets
    its schema prefixed with target.schema, so a CI run against a per-PR
    dataset can never collide with or write into the real bronze/silver/gold.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.name == 'dev' -%}
        {%- if custom_schema_name is none -%}
            {{ target.schema }}
        {%- else -%}
            {{ custom_schema_name | trim }}
        {%- endif -%}
    {%- elif custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
