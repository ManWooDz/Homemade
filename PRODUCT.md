# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

HomeMade is usable across age groups, with a primary focus on students, teenagers, and working-age people who want to cook for themselves and save money. They use it when they have ingredients at home but do not know what to cook, or when they want to make a specific dish and need a recipe that fits what they have, their preferences, and their dietary constraints.

## Product Purpose

HomeMade turns ingredients a user already has into practical recipes they can actually cook. It also supports starting from a desired dish. Success means helping the user decide what to make, use available ingredients effectively, spend less on food, and receive a recipe suited to their preferences and constraints.

## Positioning

HomeMade combines generative recipe creation with Thai food context and grounded checks. Its distinguishing mechanism is not merely suggesting a dish: generated recipes pass through ingredient, cooking, flavor, nutrition, and allergen validation, while nutrition data and user feedback make the result more verifiable and personal over time.

## Operating Context

- The user manages ingredients in a personal fridge inventory, including manual entry and barcode-assisted entry for packaged food.
- The user can select ingredients to generate a recipe, choose an existing base menu, or request a dish they want to cook.
- Onboarding and profile data capture cuisine preferences, dietary restrictions and allergies, available equipment, cooking frequency, and cooking goals.
- The product is a mobile-first web application intended for narrow phone-sized layouts, currently capped at 430 px in the established frontend convention.
- This is a two-person academic capstone. Its measured contributions are the Nutrition Engine, allergen validation, and the critic-feedback retry loop; other features are the product envelope rather than additional research contributions.

## Capabilities and Constraints

- Frontend: React, Vite, and Tailwind CSS. Backend: FastAPI with PostgreSQL through SQLAlchemy and Alembic. Recipe generation uses Gemini.
- Recipes can be generated from available ingredients and personalized preferences, validated through the existing six-stage pipeline, saved to history, rated, and favorited.
- Nutrition calculation grounds ingredient quantities against INMU data with USDA fallback and exposes partial estimation when full grounding is unavailable.
- Allergen validation combines a rule-based safety floor with a PostgreSQL knowledge graph. It must not be presented as a medical guarantee.
- The product is Thai-first in language and food context. It may support other cuisine preferences without weakening its Thai-context positioning.
- The current repository is a development and evaluation system, not evidence of a production deployment.
- YOLO-based food recognition is no longer part of the product direction.

## Brand Commitments

- Product name: HomeMade.
- Primary product language: Thai.
- The existing HomeMade logo is a committed brand asset and appears across multiple screens: `frontend/src/assets/HomeMade_Logo.png`.
- Preserve a practical, approachable voice suitable for people deciding what to cook at home.

## Evidence on Hand

- The repository contains runnable frontend flows for authentication, onboarding, fridge management, recipe discovery and generation, cooking steps, history, ratings, favorites, and profile preferences.
- The backend contains the validation pipeline, nutrition data pipeline, allergen knowledge graph, personalization logic, evaluation fixtures, and automated tests documented in `spec.md`.
- `README.md`, `spec.md`, and `MEMORY.md` record the implemented system, verification history, limitations, and operational lessons.
- No customer testimonials, commercial adoption claims, or production deployment evidence are established in the repository; future product surfaces must not fabricate them.

## Product Principles

1. Start with what the user already has and help them waste less and spend less.
2. Recommend food that is practical to cook, not merely plausible-sounding AI output.
3. Personalize around real preferences, equipment, and dietary constraints.
4. Make nutrition and allergen reasoning inspectable, with uncertainty stated honestly.
5. Keep the core experience fast and comfortable on a phone.
