# TypeScript Patterns for Scalable Applications

## Introduction

TypeScript extends JavaScript with a powerful static type system. Used well, it eliminates entire categories of runtime errors, makes refactoring safe, and turns your IDE into a powerful collaborator. Used carelessly, it becomes a tax that slows you down without delivering the safety benefits. This document covers the patterns that experienced TypeScript engineers use to get the full benefit of the type system.

## Generics

Generics let you write code that works with many types while remaining type-safe. They are the foundation of reusable TypeScript.

A generic function captures the relationship between input and output types:

```typescript
function identity<T>(value: T): T {
  return value;
}

function first<T>(arr: T[]): T | undefined {
  return arr[0];
}
```

Generic constraints limit which types a type parameter can be. Use `extends` to constrain:

```typescript
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

const user = { id: 1, name: "Alice", email: "alice@example.com" };
const name = getProperty(user, "name");   // typed as string
const id = getProperty(user, "id");       // typed as number
// getProperty(user, "missing");          // compile error
```

Generic interfaces describe reusable contracts:

```typescript
interface Repository<T, ID> {
  findById(id: ID): Promise<T | null>;
  save(entity: T): Promise<T>;
  delete(id: ID): Promise<void>;
  findAll(options?: QueryOptions): Promise<T[]>;
}
```

## Type Inference

TypeScript's type inference is sophisticated. It often knows the type of a variable without an explicit annotation. Trust inference where it works:

```typescript
// Annotation unnecessary — TypeScript infers string[]
const names = ["Alice", "Bob", "Carol"];

// Infers the return type correctly
function add(a: number, b: number) {
  return a + b; // return type: number
}
```

But annotate explicitly at function signatures, public APIs, and when inference would produce `any`. The goal is precision: the narrowest type that accurately describes the value.

## Type Guards

Type guards narrow the type within a conditional block. They are how you safely work with union types and `unknown` values.

The `typeof` and `instanceof` operators act as built-in type guards:

```typescript
function formatValue(value: string | number): string {
  if (typeof value === "string") {
    return value.toUpperCase(); // TypeScript knows: value is string here
  }
  return value.toFixed(2); // TypeScript knows: value is number here
}
```

User-defined type guards use a return type predicate:

```typescript
interface Cat { meow(): void }
interface Dog { bark(): void }

function isCat(animal: Cat | Dog): animal is Cat {
  return "meow" in animal;
}

function makeSound(animal: Cat | Dog): void {
  if (isCat(animal)) {
    animal.meow(); // safe
  } else {
    animal.bark(); // safe
  }
}
```

For runtime validation of external data (API responses, user input), use `unknown` as the entry type and narrow it:

```typescript
async function fetchUser(id: string): Promise<User> {
  const data: unknown = await (await fetch(`/api/users/${id}`)).json();

  if (!isUser(data)) {
    throw new Error("Invalid user data from API");
  }
  return data; // narrowed to User
}
```

## Utility Types

TypeScript ships with utility types that perform common type transformations. Using them avoids repetitive manual type definitions.

`Partial<T>` makes all properties optional — useful for update operations:

```typescript
async function updateUser(id: string, updates: Partial<User>): Promise<User> {
  // Only the provided fields are updated
}
```

`Required<T>` is the opposite — all properties become required.

`Pick<T, K>` creates a type with only the specified keys:

```typescript
type UserSummary = Pick<User, "id" | "name" | "avatarUrl">;
```

`Omit<T, K>` is the inverse — all keys except the specified ones:

```typescript
type CreateUserInput = Omit<User, "id" | "createdAt" | "updatedAt">;
```

`Record<K, V>` creates a mapped object type:

```typescript
type RolePermissions = Record<"admin" | "editor" | "viewer", Permission[]>;
```

`Readonly<T>` prevents mutation — useful for function parameters you should not modify:

```typescript
function processUsers(users: Readonly<User[]>): Report {
  // users.push(...) would be a compile error
}
```

## Discriminated Unions

Discriminated unions (also called tagged unions or algebraic data types) are one of TypeScript's most powerful patterns for modeling state.

Each variant carries a discriminant property — a literal type that uniquely identifies it:

```typescript
type LoadingState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: User[] }
  | { status: "error"; error: string };

function renderState(state: LoadingState): string {
  switch (state.status) {
    case "idle":    return "Not started";
    case "loading": return "Loading...";
    case "success": return `Loaded ${state.data.length} users`;
    case "error":   return `Error: ${state.error}`;
    // No default needed — TypeScript verifies exhaustiveness
  }
}
```

Add exhaustiveness checking with a `never` assertion:

```typescript
function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${JSON.stringify(x)}`);
}

// In the switch: default: return assertNever(state);
```

This gives you a compile error if you add a new variant but forget to handle it.

## Mapped Types

Mapped types iterate over the keys of another type and transform them. They are the basis for many utility types and custom transformations.

```typescript
type Nullable<T> = { [K in keyof T]: T[K] | null };
type Stringified<T> = { [K in keyof T]: string };

// Conditional mapped type
type DeepReadonly<T> = {
  readonly [K in keyof T]: T[K] extends object ? DeepReadonly<T[K]> : T[K];
};
```

Template literal types combine string literals in mapped types:

```typescript
type EventName<T extends string> = `on${Capitalize<T>}`;
type UserEvents = EventName<"click" | "focus" | "blur">;
// "onClick" | "onFocus" | "onBlur"
```

## React Hooks Patterns

In React with TypeScript, hooks are more powerful with precise typing.

Generic hooks provide type safety for data-fetching abstractions:

```typescript
function useFetch<T>(url: string): { data: T | null; loading: boolean; error: Error | null } {
  const [state, setState] = useState<{
    data: T | null;
    loading: boolean;
    error: Error | null;
  }>({ data: null, loading: true, error: null });

  useEffect(() => {
    fetch(url)
      .then(res => res.json() as Promise<T>)
      .then(data => setState({ data, loading: false, error: null }))
      .catch(error => setState({ data: null, loading: false, error }));
  }, [url]);

  return state;
}
```

Use `useReducer` with discriminated unions for complex state:

```typescript
type Action =
  | { type: "increment" }
  | { type: "decrement" }
  | { type: "reset"; payload: number };

function reducer(state: number, action: Action): number {
  switch (action.type) {
    case "increment": return state + 1;
    case "decrement": return state - 1;
    case "reset":     return action.payload;
  }
}
```

## Strict Mode

Always enable strict mode in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

`strict: true` enables: `noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`, `strictPropertyInitialization`, and others. Every one of these prevents real bugs.

`noUncheckedIndexedAccess` makes array and object index access return `T | undefined` rather than `T`. This forces you to handle the case where an index is out of bounds.

`exactOptionalPropertyTypes` distinguishes `{ x?: string }` (x may be absent) from `{ x: string | undefined }` (x must be present but may be undefined). A subtle but important distinction.

## Module Patterns

Organize TypeScript modules for clarity and composability.

Use barrel files (`index.ts`) to re-export a module's public API:

```typescript
// features/users/index.ts
export { UserCard } from "./UserCard";
export { useUserStore } from "./useUserStore";
export type { User, UserRole } from "./types";
// Do NOT export internal helpers
```

Separate types from implementation with `.types.ts` files for large domains. This prevents circular imports because types-only files rarely import implementation files.

Avoid using `namespace` in modern TypeScript. ES modules provide the same isolation without the additional complexity.

Use `const enum` sparingly. It inlines values at compile time but breaks with `isolatedModules` (required by tools like Babel and esbuild). Prefer `enum` or typed string unions.
