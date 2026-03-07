# Rust Ownership, Borrowing, and Memory Safety

## Introduction

Rust's ownership system is its most distinctive feature and the source of its most powerful guarantee: memory safety without a garbage collector. Understanding ownership, borrowing, and lifetimes is not optional — it is the foundation upon which every other Rust concept is built. This document covers these core mechanisms with practical examples and the mental models that make them intuitive.

## Ownership Rules

Rust enforces three fundamental ownership rules at compile time:

1. Every value in Rust has exactly one owner.
2. When the owner goes out of scope, the value is dropped.
3. There can only be one owner at a time.

These rules prevent dangling pointers, double frees, and use-after-free errors — the entire class of memory safety bugs that plague C and C++.

```rust
fn main() {
    let s1 = String::from("hello");
    let s2 = s1; // s1 is moved into s2; s1 is no longer valid
    // println!("{}", s1); // compile error: value borrowed after move
    println!("{}", s2); // fine
}
```

The `String` type owns heap-allocated data. When `s1` is assigned to `s2`, ownership transfers (moves). `s1` is invalidated. This is a compile-time check — no runtime cost.

Types that implement the `Copy` trait are duplicated rather than moved. Primitive types like `i32`, `bool`, `f64`, and `char` are `Copy`. They are small enough that copying them is cheap, so Rust copies them automatically.

## Borrowing

Ownership transfer is often too restrictive. You frequently want to pass a value to a function without giving up ownership. Borrowing lets you do this.

A reference (`&T`) borrows a value without taking ownership:

```rust
fn calculate_length(s: &String) -> usize {
    s.len()
}

fn main() {
    let s = String::from("hello");
    let len = calculate_length(&s); // borrow s
    println!("'{}' has length {}", s, len); // s still valid
}
```

Rust enforces two borrowing rules:
- You can have any number of immutable references (`&T`) at the same time.
- You can have exactly one mutable reference (`&mut T`) at a time.
- You cannot have both immutable and mutable references simultaneously.

These rules prevent data races at compile time. A data race requires two or more pointers accessing the same data where at least one is writing and the accesses are unsynchronized. Rust's borrow checker makes this impossible.

```rust
let mut s = String::from("hello");
let r1 = &s;      // immutable borrow
let r2 = &s;      // another immutable borrow — fine
// let r3 = &mut s; // compile error: cannot borrow as mutable while immutably borrowed
println!("{} {}", r1, r2);
// r1 and r2 are no longer used after this point
let r3 = &mut s;  // now fine
r3.push_str(", world");
```

## Lifetimes

Lifetimes are Rust's way of ensuring that references are always valid. They annotate the relationship between the lifetimes of multiple references.

The borrow checker uses lifetime annotations to verify that references do not outlive the data they point to:

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

The lifetime annotation `'a` says: the returned reference lives at least as long as both input references. The caller guarantees this — the borrow checker verifies it.

Lifetime elision rules allow the compiler to infer lifetimes in most common cases. You only need explicit annotations when the compiler cannot determine them automatically. Three elision rules cover the majority of functions:

1. Each reference parameter gets its own lifetime.
2. If there is exactly one input lifetime, it is assigned to all output lifetimes.
3. If one of multiple input lifetimes is `&self` or `&mut self`, its lifetime is assigned to all output lifetimes.

`'static` is the longest lifetime — it lasts for the entire duration of the program. String literals have `'static` lifetime because they are compiled into the binary.

## Traits

Traits define shared behavior. They are Rust's equivalent of interfaces in other languages, but more powerful because they can be implemented for types you did not define (with the orphan rule limiting this to prevent conflicts).

```rust
trait Summary {
    fn summarize(&self) -> String;
    fn author(&self) -> String {
        String::from("(unknown)")  // default implementation
    }
}

struct Article {
    title: String,
    content: String,
}

impl Summary for Article {
    fn summarize(&self) -> String {
        format!("{}: {}", self.title, &self.content[..100])
    }
}
```

Trait bounds constrain generic types:

```rust
fn notify(item: &impl Summary) {
    println!("Breaking: {}", item.summarize());
}

// equivalent with where clause for clarity in complex signatures:
fn notify_all<T>(items: &[T]) where T: Summary + Clone {
    for item in items {
        println!("{}", item.clone().summarize());
    }
}
```

## Enums and Pattern Matching

Rust's enums are algebraic data types — each variant can carry different data. Combined with pattern matching, they enable expressive, exhaustive handling of every possible case.

```rust
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(u8, u8, u8),
}

fn process(msg: Message) {
    match msg {
        Message::Quit => println!("Quitting"),
        Message::Move { x, y } => println!("Moving to ({}, {})", x, y),
        Message::Write(text) => println!("Writing: {}", text),
        Message::ChangeColor(r, g, b) => println!("Color: rgb({},{},{})", r, g, b),
    }
}
```

The compiler enforces exhaustiveness. If you forget a variant, your code does not compile. This is a compile-time guarantee that you have handled every case.

`Option<T>` and `Result<T, E>` are the two most important enums in Rust's standard library. `Option` replaces null. `Result` replaces exceptions.

## Error Handling

Rust has no exceptions. Errors are values. Functions that can fail return `Result<T, E>`. The caller is forced to handle both success and failure.

The `?` operator propagates errors up the call stack:

```rust
use std::fs;
use std::io;

fn read_username_from_file() -> Result<String, io::Error> {
    let contents = fs::read_to_string("username.txt")?;
    Ok(contents.trim().to_string())
}
```

For libraries, use `thiserror` to define error types with clear messages:

```rust
use thiserror::Error;

#[derive(Debug, Error)]
enum DatabaseError {
    #[error("record not found: {id}")]
    NotFound { id: String },
    #[error("connection failed: {0}")]
    ConnectionFailed(#[from] sqlx::Error),
}
```

For applications (binaries), use `anyhow` for ergonomic error handling with context:

```rust
use anyhow::{Context, Result};

fn load_config(path: &str) -> Result<Config> {
    let text = fs::read_to_string(path)
        .with_context(|| format!("failed to read config from {}", path))?;
    toml::from_str(&text).context("failed to parse config as TOML")
}
```

## Async Runtime

Rust's async/await is built on futures. A future is a value that represents an asynchronous computation. Futures are lazy — they do nothing until polled.

An async runtime (Tokio is the de-facto standard) drives futures to completion by polling them on worker threads. Annotate the entry point with `#[tokio::main]`:

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let response = reqwest::get("https://api.example.com/data").await?;
    let data: serde_json::Value = response.json().await?;
    println!("{:#}", data);
    Ok(())
}
```

Spawn concurrent tasks with `tokio::spawn`. Tasks run on the runtime's thread pool:

```rust
let handle = tokio::spawn(async move {
    expensive_computation().await
});
let result = handle.await?;
```

## Smart Pointers

When a single value needs multiple owners, use `Rc<T>` (single-threaded) or `Arc<T>` (multi-threaded). These implement reference counting:

```rust
use std::sync::Arc;
use tokio::sync::RwLock;

// Shared, mutable state across async tasks
let shared_cache: Arc<RwLock<HashMap<String, String>>> = Arc::new(RwLock::new(HashMap::new()));

let cache_clone = Arc::clone(&shared_cache);
tokio::spawn(async move {
    let mut cache = cache_clone.write().await;
    cache.insert("key".to_string(), "value".to_string());
});
```

`Box<T>` allocates on the heap. Use it for recursive types or when you need a trait object (`Box<dyn Trait>`) for dynamic dispatch:

```rust
fn make_handler(config: &Config) -> Box<dyn RequestHandler> {
    if config.fast_mode {
        Box::new(FastHandler::new())
    } else {
        Box::new(StableHandler::new())
    }
}
```

## Unsafe Rust

The `unsafe` keyword disables Rust's safety guarantees within a block. It is necessary for FFI, raw pointer manipulation, and some performance-critical code. Treat it as a powerful escape hatch, not a convenience.

Unsafe code is not inherently incorrect — the Rust standard library is full of it. But it concentrates the responsibility for correctness on you, not the compiler. Document every unsafe block with a comment explaining why it is sound:

```rust
// SAFETY: `ptr` is non-null and properly aligned, points to a valid `T`,
// and no other references to this memory exist in this scope.
let value = unsafe { ptr.read() };
```

Keep unsafe blocks small and well-bounded. Wrap them in safe abstractions so callers never need to write unsafe code themselves.
