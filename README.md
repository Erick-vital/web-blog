# blog_web (Astro + Vercel, static)

Blog estático alimentado desde `platform_v2` (`ci_v1_blog_*.json`).

## Objetivo
Publicar artículos en web con costo mínimo (sin backend ni DB runtime), usando:
- contenido canónico en servidor
- build estático con Astro
- deploy en Vercel vía GitHub

## Ruta del repo
`/home/erickesc/repos/blog_web`

## Fuente de contenido (canónica)
- `items/by_id/ci_v1_blog_*.json`
- estructura esperada:
  - `source_type = owned.blog.post`
  - `stage` (filtrable)
  - `timestamps.created_at`
  - `artifacts.title`
  - `artifacts.content_markdown`
  - `editorial_enrichment.*` (opcional enriquecimiento)
  - `lineage.derived_from_item_ids`

## Mapeo canónico -> frontmatter markdown
El script `scripts/sync_platform_v2_blog_items.py` exporta a `src/content/blog/generated/*.md` con:
- `title <- artifacts.title`
- `description <- resumen de content_markdown`
- `pubDate <- timestamps.created_at`
- `canonical_id <- id`
- `stage <- stage`
- `topic <- editorial_enrichment.topic.primary`
- `use_case <- editorial_enrichment.use_case.primary`
- `sources <- lineage.derived_from_item_ids`
- body markdown <- `artifacts.content_markdown`

## Comandos
```bash
# 1) instalar deps
npm install

# 2) sincronizar contenido desde platform_v2
npm run sync:content

# 3) build estático
npm run build

# combo
npm run publish:static
```

## Configuración de stages
Por defecto exporta `draft,ready`.
Puedes ajustar:
```bash
python3 ./scripts/sync_platform_v2_blog_items.py --stage-allow ready
```

## Deploy en Vercel (lo que haces tú)
1. Subir este repo a GitHub.
2. En Vercel: **Add New Project** -> importar repo.
3. Framework detectado: **Astro** (build command `npm run build`, output `dist`).
4. Deploy.

### ¿Qué keys/secrets se necesitan?
Para esta v1 estática: **ninguna API key obligatoria**.
- No usamos DB/API en runtime.
- No necesitamos AWS keys ni tokens de contenido para servir el blog.

Opcional recomendado:
- definir dominio y actualizar `site` en `astro.config.mjs` (para RSS/sitemap correctos).

## Notas operativas
- Si un post ya existe y cambia el contenido en canónico, el sync lo sobreescribe (idempotente por slug+id).
- El deploy se gatilla por `git push` (si Vercel está conectado a GitHub).
