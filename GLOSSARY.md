# Homemade

Canonical language for Homemade's recipe, fridge, account and account-recovery domain. Terms here describe product meaning, not implementation details.

## Recipe Adaptation

**Allowed Recipe Ingredient**:
An ingredient the user selected or a pantry ingredient explicitly permitted by the recipe policy. An ingredient whose identity cannot be established is not assumed to be an allowed ingredient.
_Avoid_: Any nutrition alias, substring match, inferred ingredient

**Adapted Recipe**:
A recipe changed from its starting recipe to use the user's available ingredients, including a change of the main ingredient. Its name must describe the ingredients actually used rather than preserve a contradictory original name.
_Avoid_: Original recipe with a fixed protein, unchanged base recipe

**Declared Recipe Ingredient**:
An ingredient explicitly included in the generated recipe's ingredient list. Every ingredient used in the cooking instructions, including permitted pantry seasonings, must be declared; pantry permission does not make that declaration implicit.
_Avoid_: Ingredient mentioned only in a step, implicit pantry addition

**Flavor Compatibility**:
The suitability of ingredients for use together in a recipe. It concerns ingredient combinations rather than a guarantee of how much a particular person will enjoy the dish.
_Avoid_: Guaranteed deliciousness, universal bad-flavor word pair

**Seasoning Added to Taste**:
A declared recipe seasoning whose quantity is intentionally unspecified so its amount can be adjusted to taste. Excluding its unknown contribution from a numeric total does not establish that the seasoning contains no nutrients.
_Avoid_: Zero-nutrition seasoning, undeclared seasoning

**Chili Paste**:
In Homemade's ingredient catalog, roasted chili paste (น้ำพริกเผา). The catalog name does not refer to every curry paste, chili sauce or other chili mixture.
_Avoid_: Any chili mixture, curry paste

**Chives**:
In Homemade's ingredient catalog, garlic chives (กุยช่าย). This catalog meaning is distinct from green onion and does not make every product called common chives equivalent.
_Avoid_: Green onion, any onion herb

## Fridge Expiry Reminders

**Recorded Expiry Date**:
The optional, approximate expiry date recorded by the account holder for an ingredient in their fridge. It is not independent evidence that the food is safe or unsafe to eat.
_Avoid_: Verified food safety deadline, guaranteed shelf life

**Near-expiry Ingredient**:
A fridge ingredient whose recorded expiry date is today or within the next three calendar days. An ingredient whose date has passed is expired by the recorded date, a separate reminder category.
_Avoid_: Automatically selected cooking ingredient, verified fresh food

**Expiry Reminder**:
A notification about a fridge ingredient approaching, reaching or passing its recorded expiry date. Its purpose is to draw attention to the recorded date, not to certify the food's condition.
_Avoid_: Food safety verdict, automatic stock consumption

## Recipe Save Events

**Recipe History Save**:
The successful addition of a generated recipe to the account holder's recipe history. Successful recipe generation alone does not establish that this save occurred.
_Avoid_: Favorite save, generation success

**Favorite Recipe Save**:
The successful addition of a catalog recipe or a generated recipe to the account holder's favorites. Removing a favorite or repeating an already-completed addition is not a new save.
_Avoid_: Recipe history save, optimistic heart state

## Recipe History and Ratings

**History Entry**:
A generated recipe saved in the account holder's history. Its presence does not establish that the account holder cooked it or gave it a rating.
_Avoid_: Completed cooking session, rated recipe by default

**Recipe Rating**:
The account holder's current evaluation of one history entry, consisting of one to five stars and optional rating tag and recipe feedback. An entry with no rating is unrated.
_Avoid_: Catalog score, critic validation result

**Rating Tag**:
An optional short description chosen by the account holder to express how they liked a history entry's recipe. It is separate from the recipe's dietary tags.
_Avoid_: Dietary tag, allergy label

**Recipe Feedback**:
An optional written comment from the account holder accompanying a recipe rating. It is distinct from validation feedback used to correct generated recipes.
_Avoid_: Critic feedback, validation failure reason

## Recipe Timing

**Estimated Total Recipe Time**:
A reviewed approximate range of elapsed time from preparing the ingredients to food ready to eat, including cooking and waiting specified by the recipe. Ingredients described as prepared foods are ready at the start; the range is an estimate, not a measured or guaranteed duration.
_Avoid_: Active cooking time, time to make every ingredient from scratch, guaranteed completion time

## Allergen Validation

**Literal Allergen Match**:
A match to an explicitly identified allergen ingredient in the food being evaluated. Letters shared with an unrelated ingredient do not establish a match.
_Avoid_: Substring hit, floor hit

**Derived Allergen Match**:
A match to an allergen through a known constituent of an ingredient or prepared food, rather than an explicit mention of that allergen itself.
_Avoid_: KG hit, hidden-allergen guess

**Absence Claim**:
A statement that a particular allergen is absent from a particular ingredient. The statement is scoped to that ingredient and cannot override known composition or establish an exemption for other constituents.
_Avoid_: Allergen-free proof, recipe-wide exemption

## Nutrition Grounding

**Nutrition Proxy**:
A different food whose composition is used to approximate the composition of the requested ingredient.
_Avoid_: Exact equivalent, confirmed ingredient composition

**Fully Grounded Nutrition**:
Nutrition calculated from correctly identified food records, gram quantities supported by mass units or cited ingredient-specific portions/densities, and complete source-backed macros without nutrition proxies or values imputed to fill source gaps. This describes the grounding of the calculation, not independent proof that every source value is accurate.
_Avoid_: Clinically verified nutrition, exact nutrition

**Source-backed Macro**:
A nutrient value published by the identified food-composition source, including a calculated value that the source itself publishes.
_Avoid_: Imputed macro, independently verified nutrient value

**Imputed Macro**:
A nutrient value calculated by Homemade to fill a value missing from the food-composition source. Its calculation method is part of its provenance, and the value remains an estimate.
_Avoid_: Source-backed macro, measured nutrient value

**Partially Estimated Nutrition**:
Nutrition whose calculation includes an estimate or unresolved information, including a nutrition proxy, an approximate gram conversion, or an imputed macro.
_Avoid_: Fully grounded nutrition, exact nutrition

## Password Recovery

**Password-reset OTP**:
A short-lived, six-digit one-time code used to prove control of the email address associated with an account.
_Avoid_: Reset token, email token, verification email

**Delivery Accepted**:
The email provider has accepted a password-reset message for delivery; this does not mean the message reached the recipient's inbox.
_Avoid_: Delivered, received, inbox-confirmed

**Delivery Unconfirmed**:
The system did not receive reliable confirmation that the email provider accepted a password-reset message; this does not prove that the provider rejected or failed to send it.
_Avoid_: Not sent, definitely failed, rejected

**Reset Ticket**:
A short-lived, single-use proof issued after a correct password-reset OTP is verified, authorizing one password change.
_Avoid_: OTP, access token, reset OTP

**Generic Authentication Response**:
An outward response whose status and shape do not reveal whether an account exists or whether password-reset delivery succeeded.
_Avoid_: Success confirmation, delivery confirmation

## Account Profile

**Application Language**:
The account holder's chosen Thai or English language for Homemade's interface, including controls and application messages. It does not change the original language of recipes, catalog content or text entered by the user.
_Avoid_: Recipe language, automatic recipe translation

**Profile Picture**:
An image uploaded by the account holder to represent their account in Homemade. It belongs to the account rather than a particular browser or device.
_Avoid_: Ingredient image, device-only avatar

**Display Name**:
The name an account holder chooses to see on their Homemade profile. Different account holders may use the same name; it is separate from their login email and need not be a legal name.
_Avoid_: Login username, unique account name, legal name
