# Glean Help Center (2025 Preview)

Glean Help Center proof of concept. This site is built using Mintlify and aggregates all publicly available documentation from help.glean.com, support.glean.com, developers.glean.com, and the previous 2023-2024 Mkdocs Help Center preview - all into a single site.

The focus is on speed, ease of use, and standardizing the user experience across all Glean documentation.

### Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mintlify) to preview the documentation changes locally. To install, use the following command

```
npm i -g mintlify
```

Run the following command at the root of your documentation (where mint.json is)

```
mintlify dev --port 8888
```