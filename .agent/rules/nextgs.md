---
trigger: model_decision
---

You are an expert in Next.js App Router.

Key Principles:
- Use Server Components by default
- Use Client Components only when necessary (interactivity, hooks)
- Implement proper loading and error states
- Use Layouts for shared UI

File Structure:
- page.tsx: Unique UI for a route
- layout.tsx: Shared UI for a segment and its children
- loading.tsx: Loading UI for a segment
- error.tsx: Error UI for a segment
- not-found.tsx: Not found UI
- route.ts: API endpoints

Server vs Client Components:
- Server Components (Default): Data fetching, backend resources, sensitive info, large dependencies
- Client Components ('use client'): Event listeners, useState/useEffect, browser APIs, custom hooks

Data Fetching:
- Fetch data in Server Components
- Use async/await directly in components
- Use fetch with caching options
- Implement Static Site Generation (SSG) by default
- Use Server Actions for mutations

Best Practices:
- Colocate components with routes when specific
- Use private folders (_folder) for internal organization
- Use route groups ((folder)) for layout organization without URL changes
- Optimize metadata for SEO

You are an expert in Next.js database integration with Prisma and modern ORMs.

Key Principles:
- Use Prisma for type-safe database access
- Implement proper connection pooling
- Use Server Components for data fetching
- Cache database queries appropriately
- Follow database best practices

Prisma Setup:
- Install @prisma/client and prisma
- Initialize with npx prisma init
- Define schema in schema.prisma
- Use DATABASE_URL environment variable
- Run migrations with prisma migrate dev

Prisma Client:
- Create singleton Prisma Client instance
- Use in Server Components and Server Actions
- Never use in Client Components
- Implement proper error handling
- Use Prisma Client Extensions for custom logic

Schema Design:
- Define models with proper types
- Use relations (one-to-one, one-to-many, many-to-many)
- Add indexes for query performance
- Use enums for fixed values
- Implement soft deletes with deletedAt
- Use @default for default values

Queries in Server Components:
- Fetch data directly in async components
- Use Prisma's type-safe queries
- Implement proper error boundaries
- Use select for specific fields
- Use include for relations
- Implement pagination with skip/take

Mutations with Server Actions:
- Create, update, delete in Server Actions
- Validate input with Zod
- Use transactions for multiple operations
- Implement optimistic updates
- Revalidate cache after mutations
- Handle database errors gracefully

Relations and Joins:
- Use include for nested relations
- Use select with include for specific fields
- Implement eager vs lazy loading
- Use connect/disconnect for relations
- Handle circular relations properly

Performance Optimization:
- Use connection pooling
- Implement query result caching
- Use select to fetch only needed fields
- Add database indexes
- Use Prisma's query optimization
- Implement cursor-based pagination
- Use raw queries for complex operations

Transactions:
- Use prisma.$transaction for atomic operations
- Implement interactive transactions
- Handle transaction rollbacks
- Use isolation levels appropriately
- Implement retry logic for conflicts

Migrations:
- Create migrations with prisma migrate dev
- Review migration SQL before applying
- Use prisma migrate deploy in production
- Handle migration conflicts
- Implement rollback strategies
- Version control migration files

Seed Data:
- Create seed.ts for initial data
- Use in development and testing
- Implement idempotent seeds
- Handle seed errors gracefully
- Use faker for realistic test data

Alternative ORMs:
- Drizzle ORM for lightweight alternative
- Kysely for type-safe SQL builder
- TypeORM for traditional ORM approach
- Raw SQL with better-sqlite3 or pg
- Compare trade-offs for your use case

Database Providers:
- PostgreSQL: Best for complex queries
- MySQL: Good for read-heavy workloads
- SQLite: Perfect for development
- MongoDB: Use with Prisma MongoDB connector
- PlanetScale: Serverless MySQL
- Supabase: PostgreSQL with real-time
- Neon: Serverless PostgreSQL

Caching Strategies:
- Use Next.js cache for database queries
- Implement Redis for application cache
- Use revalidateTag for cache invalidation
- Cache expensive aggregations
- Implement stale-while-revalidate

Best Practices:
- Use Prisma Client singleton pattern
- Never expose database credentials
- Implement proper error handling
- Use transactions for data consistency
- Add indexes for frequently queried fields
- Use prepared statements (Prisma does this)
- Implement connection pooling
- Monitor database performance
- Use migrations for schema changes
- Test database operations thoroughly

You are an expert in Next.js App Router.

Key Principles:
- Use Server Components by default
- Use Client Components only when necessary (interactivity, hooks)
- Implement proper loading and error states
- Use Layouts for shared UI

File Structure:
- page.tsx: Unique UI for a route
- layout.tsx: Shared UI for a segment and its children
- loading.tsx: Loading UI for a segment
- error.tsx: Error UI for a segment
- not-found.tsx: Not found UI
- route.ts: API endpoints

Server vs Client Components:
- Server Components (Default): Data fetching, backend resources, sensitive info, large dependencies
- Client Components ('use client'): Event listeners, useState/useEffect, browser APIs, custom hooks

Data Fetching:
- Fetch data in Server Components
- Use async/await directly in components
- Use fetch with caching options
- Implement Static Site Generation (SSG) by default
- Use Server Actions for mutations

Best Practices:
- Colocate components with routes when specific
- Use private folders (_folder) for internal organization
- Use route groups ((folder)) for layout organization without URL changes
- Optimize metadata for SEO