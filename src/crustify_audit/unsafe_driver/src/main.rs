//! Canonical rustc driver for `crustify-audit unsafe`.
//!
//! Changes to the deterministic safety pass belong here.
//!
//! PoC: a rustc driver (HIR + typeck) that counts three properties of a Rust
//! crate that the regex/`syn` approaches cannot do precisely:
//!
//!   * `unsafe_blocks`        - number of `unsafe { ... }` blocks
//!   * `unsafe_block_stmts`   - statements lexically inside unsafe blocks
//!   * `unsafe_block_lines`   - source lines spanned by unsafe blocks (outermost)
//!   * `raw_ptr_derefs`       - dereferences `*p` where `p: *const T | *mut T`
//!                              (decided by the *type* of the operand via typeck,
//!                              so `*Box`/`*&`/`Deref` impls are NOT counted)
//!   * `raw_ptr_derefs_outside_impl` - of those, the subset outside any
//!                              `impl`/trait body (port-body raw access vs. the
//!                              sanctioned accessor/seam centralisation)
//!
//! Run as a rustc-compatible front end: it compiles the given file/crate and
//! prints the metrics as JSON in `after_analysis`. See `run.sh`.
#![feature(rustc_private)]

extern crate rustc_abi;
extern crate rustc_driver;
extern crate rustc_hir;
extern crate rustc_interface;
extern crate rustc_middle;
extern crate rustc_span;

use rustc_abi::ExternAbi;
use rustc_driver::{Callbacks, Compilation};
use rustc_hir as hir;
use rustc_hir::def::DefKind;
use rustc_hir::intravisit::{self, Visitor};
use rustc_middle::middle::codegen_fn_attrs::CodegenFnAttrFlags;
use rustc_middle::ty::{self, Ty, TyCtxt, TypeckResults};
use rustc_span::def_id::DefId;
use rustc_span::hygiene::{ExpnKind, MacroKind};
use rustc_span::Span;
use std::collections::{HashMap, HashSet};

/// FFI-seam conversion routines: raw pointers in these signatures are the
/// expected boundary, not a smell. Mirrors `ffibox`'s seam surface — the
/// `define_ctype!` handles, the owners (`CBox`, `CStrBox`, `CVec`, `CArc`,
/// `CGuardedArc`) and the run views — plus the names the ported trees add for
/// callback wrappers.
const SEAM_FNS: &[&str] = &[
    // ffibox: outbound, Rust-side pointee or the C type (`as_c_ptr`)
    "as_ptr",
    "as_mut_ptr",
    "as_c_ptr",
    "as_non_null",
    // the run views' plain-element pointers
    "as_elem_ptr",
    "as_mut_elem_ptr",
    // the handles' erasure trio: erase shared / erase exclusive / reconstitute
    "as_void_ptr",
    "as_mut_void_ptr",
    "from_void_ptr",
    // inbound: borrow (`from_ptr`) or adopt (`from_raw*`, `from_c*`)
    "from_ptr",
    "from_raw",
    "from_raw_with",
    "from_raw_parts",
    "from_raw_parts_with",
    "from_c",
    "from_c_with",
    // surrender ownership
    "into_raw",
    "into_raw_with",
    "into_raw_parts",
    "into_raw_parts_with",
    "into_c",
    // ported trees: safe callback wrapper -> raw C fn pointer
    "to_raw",
    // unsafe lifecycle trait methods: release, clone, share, lock and dispose
    // hooks whose `unsafe fn` signature the trait fixes, so an implementation
    // cannot be safe
    "c_drop",
    "c_drop_len",
    "c_dup",
    "c_clone_len",
    "c_up_ref",
    "c_is_sole_owner",
    "c_lock",
    "c_unlock",
    "c_dispose",
];

fn is_seam_fn(tcx: TyCtxt<'_>, did: DefId) -> bool {
    tcx.opt_item_name(did)
        .is_some_and(|n| SEAM_FNS.contains(&n.as_str()))
}

/// True if `t` is `PhantomData<..>` -- a ZST, so it is not the wrapper's
/// storage and must be skipped when deciding the storage shape.
fn is_phantom(tcx: TyCtxt<'_>, t: Ty<'_>) -> bool {
    matches!(t.kind(), ty::TyKind::Adt(d, _)
        if tcx.item_name(d.did()).as_str() == "PhantomData")
}

/// True if `W` is a TYPE wrapper: a wrapper whose storage IS the C object's
/// bytes (an inline `ffi::T`, as in a `define_ctype!` layout type), as opposed
/// to a POINTER to it.
///
/// This is the distinction that decides whether a reference is a hazard at all.
/// `&W` over inline storage asserts `noalias` / `readonly` / validity over
/// memory C may write through a pointer it retains; `&W` over a pointer slot
/// asserts it over Rust-owned storage, which is harmless -- that is exactly why
/// access goes through the borrowed handles, which hold the pointer by value.
///
/// Membership is keyed on `CCell` rather than on the field shape, because
/// `CCell` is what the framework itself treats as a wrapper (`CBox<W, D>`, the
/// `Ref`/`Mut` associated types) and because it resolves AFTER macro expansion,
/// so `define_ctype!`-generated and hand-written wrappers are seen alike. The
/// field shape then splits that set; a wrapper with no non-ZST field is counted
/// as a type wrapper, which keeps the target at 0 rather than silently exempting
/// it.
fn is_type_wrapper(tcx: TyCtxt<'_>, did: DefId) -> bool {
    // A LAYOUT newtype -- storage IS the C object's bytes. `&W` / `&mut W` over
    // it asserts noalias / readonly / validity on memory C may write, so this is
    // the set where a reference is forbidden. A HANDLE holds the pointer by
    // value, covers Rust-owned storage, and is not counted.
    //
    // Decided structurally (see `structural_wrapper`), so a hand-written layout
    // newtype that never declares `CCell` is policed like a generated one.
    matches!(structural_wrapper(tcx, did), Some((true, _)))
}

/// True if `t` is `&W` or `&mut W` where `W` is a LAYOUT newtype (see
/// `structural_wrapper`). Catches the `&self` / `&mut self` receiver (whose
/// type is `&Self` / `&mut Self` = `&W` / `&mut W`) and explicit reference
/// params alike.
///
/// A reference of EITHER kind over a wrapped C object asserts something about
/// memory C may write through a pointer it retains -- `noalias` and `readonly`
/// on the shared form, `noalias` on the exclusive one, and validity on both.
/// Access goes through the borrowed handles instead, which hold the pointer by
/// value and so cover Rust-owned storage. This metric should be 0.
///
/// A reference to a POINTER wrapper is not counted: see `is_type_wrapper`.
/// The accessors the conventions give a layout value: `as_ref(&self)` /
/// `as_mut(&mut self)` hand out the borrowed handles over a `Foo` that Rust
/// owns. A `&Foo` / `&mut Foo` in their signature is the sanctioned use.
const REF_ACCESSORS: &[&str] = &["as_ref", "as_mut"];

/// Standard value traits whose methods take `&self` (and `&Self`) by
/// definition: implementing them on a layout value, derived or by hand, is
/// sanctioned. Matched on the trait's own crate (`core` / `alloc` / `std`).
const STD_VALUE_TRAITS: &[&str] =
    &["Clone", "PartialEq", "Eq", "PartialOrd", "Ord", "Hash", "Debug"];

/// True when a `&W` in `did`'s signature is sanctioned: `did` is one of the
/// `REF_ACCESSORS`, or a method of an impl of one of the `STD_VALUE_TRAITS`.
fn ref_to_wrapper_sanctioned(tcx: TyCtxt<'_>, did: DefId) -> bool {
    if tcx.opt_item_name(did).is_some_and(|n| REF_ACCESSORS.contains(&n.as_str())) {
        return true;
    }
    let Some(parent) = tcx.opt_parent(did) else {
        return false;
    };
    if !matches!(tcx.def_kind(parent), DefKind::Impl { of_trait: true }) {
        return false;
    }
    let tr = tcx.impl_trait_ref(parent).skip_binder().def_id;
    matches!(tcx.crate_name(tr.krate).as_str(), "core" | "alloc" | "std")
        && STD_VALUE_TRAITS.contains(&tcx.item_name(tr).as_str())
}

/// True if `t` holds a reference to a layout newtype anywhere: `&W`, `&mut W`,
/// `&[W]`, or one nested in a generic, tuple or array (`Option<&W>`).
fn contains_ref_to_type_wrapper(tcx: TyCtxt<'_>, t: Ty<'_>) -> bool {
    let is_w = |t: Ty<'_>| matches!(t.kind(), ty::TyKind::Adt(d, _) if is_type_wrapper(tcx, d.did()));
    match t.kind() {
        ty::TyKind::Ref(_, inner, _) => match inner.kind() {
            _ if is_w(*inner) => true,
            ty::TyKind::Slice(e) | ty::TyKind::Array(e, _) if is_w(*e) => true,
            _ => contains_ref_to_type_wrapper(tcx, *inner),
        },
        // a zero-sized marker such as a handle's `PhantomData<&'a mut W>` holds no reference
        ty::TyKind::Adt(d, _) if tcx.item_name(d.did()).as_str() == "PhantomData" => false,
        ty::TyKind::Adt(_, args) => args.types().any(|a| contains_ref_to_type_wrapper(tcx, a)),
        ty::TyKind::Tuple(tys) => tys.iter().any(|a| contains_ref_to_type_wrapper(tcx, a)),
        ty::TyKind::Array(e, _) | ty::TyKind::Slice(e) => contains_ref_to_type_wrapper(tcx, *e),
        _ => false,
    }
}

/// True when `span` comes from generated source compiled into the crate --
/// bindings `include!`d from the build script's `OUT_DIR`, or a committed
/// `bindings.rs` -- which nobody writes by hand and the audit does not judge.
fn in_generated_file(tcx: TyCtxt<'_>, span: Span) -> bool {
    let (file, _) = span_site(tcx, span.source_callsite());
    // Cargo sets OUT_DIR for a crate with a build script; it is where bindgen
    // output is written before `include!` pulls it in.
    std::env::var("OUT_DIR").is_ok_and(|out| !out.is_empty() && file.starts_with(&out))
        || file.ends_with("bindings.rs")
}

/// Raw-pointer positions in the fields of a struct or union the crate declares
/// (nested ones included, as for signatures), counted into `raw_ptr_fields` and
/// classified like a signature position: a handle stores its pointer by design,
/// so its fields are seam; elsewhere a field is pub smell when it is reachable
/// from outside the crate, else private smell. `c_void` and wrapped-pointee
/// positions feed the same `void_ptr_*` and `raw_ptr_wrapped` counters.
fn count_raw_ptr_fields(
    tcx: TyCtxt<'_>,
    did: DefId,
    wrapped_c: &HashSet<DefId>,
    c: &mut Counts,
    sites: &mut Sites,
) {
    if in_generated_file(tcx, tcx.def_span(did)) {
        return;
    }
    let handle = matches!(structural_wrapper(tcx, did), Some((false, _)));
    for f in tcx.adt_def(did).all_fields() {
        let ft = tcx.type_of(f.did).instantiate_identity().skip_norm_wip();
        let mut pointees = Vec::new();
        raw_pointees(tcx, ft, &mut pointees);
        if pointees.is_empty() {
            continue;
        }
        let site = counter_site(tcx, tcx.def_span(f.did));
        let exported = f.did.as_local().is_some_and(|l| tcx.effective_visibilities(()).is_exported(l));
        for p in pointees {
            c.raw_ptr_fields += 1;
            sites.add("raw_ptr_fields", site.clone());
            let void = is_c_void(tcx, p);
            if handle {
                c.raw_ptr_seam += 1;
                sites.add("raw_ptr_seam", site.clone());
                if void {
                    c.void_ptr_seam += 1;
                    sites.add("void_ptr_seam", site.clone());
                }
                continue;
            }
            if exported {
                c.raw_ptr_pub_smell += 1;
                sites.add("raw_ptr_pub_smell", site.clone());
                if void {
                    c.void_ptr_pub_smell += 1;
                    sites.add("void_ptr_pub_smell", site.clone());
                }
            } else {
                c.raw_ptr_priv_smell += 1;
                sites.add("raw_ptr_priv_smell", site.clone());
                if void {
                    c.void_ptr_priv_smell += 1;
                    sites.add("void_ptr_priv_smell", site.clone());
                }
            }
            if matches!(p.kind(), ty::TyKind::Adt(d, _) if wrapped_c.contains(&d.did())) {
                c.raw_ptr_wrapped += 1;
                sites.add("raw_ptr_wrapped", site.clone());
            }
        }
    }
}

/// True if `t` is a raw pointer or a `NonNull`.
fn is_raw_or_non_null(tcx: TyCtxt<'_>, t: Ty<'_>) -> bool {
    t.is_raw_ptr()
        || matches!(t.kind(), ty::TyKind::Adt(d, _) if tcx.item_name(d.did()).as_str() == "NonNull")
}

fn is_ref_to_type_wrapper(tcx: TyCtxt<'_>, t: Ty<'_>) -> bool {
    if let ty::TyKind::Ref(_, pointee, _) = t.kind() {
        if let ty::TyKind::Adt(def, _) = pointee.kind() {
            return is_type_wrapper(tcx, def.did());
        }
    }
    false
}

/// The pointees of every raw pointer position in `t`: `t` itself when it is a
/// raw pointer, else those reached through references, generic arguments
/// (`Option<*const T>`), tuples, arrays and slices. A raw pointer is one
/// position whatever it points to (`*mut *mut T` counts once), and fn-pointer
/// types are not entered: their parameters are the callback's interface, not
/// data this signature passes.
fn raw_pointees<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>, out: &mut Vec<Ty<'tcx>>) {
    match t.kind() {
        ty::TyKind::RawPtr(p, _) => out.push(*p),
        ty::TyKind::Ref(_, inner, _) => raw_pointees(tcx, *inner, out),
        // `PhantomData<*const T>` is a zero-sized marker (opting out of
        // `Send`/`Sync`, say): it stores no pointer.
        ty::TyKind::Adt(d, _) if tcx.item_name(d.did()).as_str() == "PhantomData" => {}
        ty::TyKind::Adt(_, args) => {
            for a in args.types() {
                raw_pointees(tcx, a, out)
            }
        }
        ty::TyKind::Tuple(tys) => {
            for a in tys.iter() {
                raw_pointees(tcx, a, out)
            }
        }
        ty::TyKind::Array(e, _) | ty::TyKind::Slice(e) => raw_pointees(tcx, *e, out),
        _ => {}
    }
}

/// True if `p` (a pointee) is `c_void`.
fn is_c_void(tcx: TyCtxt<'_>, p: Ty<'_>) -> bool {
    matches!(p.kind(), ty::TyKind::Adt(def, _) if tcx.item_name(def.did()).as_str() == "c_void")
}

/// True if the pointee `p` is a C type that has a wrapper
/// (i.e. a safe wrapper exists for it) — or is itself such a wrapper.
fn pointee_has_wrapper(tcx: TyCtxt<'_>, p: Ty<'_>, wrapped_c: &HashSet<DefId>) -> bool {
    match p.kind() {
        ty::TyKind::Adt(def, _) => wrapped_c.contains(&def.did()) || is_wrapper(tcx, def.did()),
        _ => false,
    }
}

/// The wrapper inventory of the current crate: `wrapper ADT -> the C types it
/// wraps`, empty where the wrapper names no ADT (`*mut c_void`) — a LAYOUT
/// newtype may carry several. Key presence IS `is_wrapper`; the flattened
/// values are `wrapped_c`.
type Wrappers = HashMap<DefId, Vec<DefId>>;

/// Structural inventory: every local struct `structural_wrapper` admits.
///
/// Nothing here reads a trait, an associated item, or a type name from ffibox,
/// so a hand-written wrapper and a `define_ctype!` one are found alike, and the
/// pass carries no dependency on the framework it audits.
fn scan_structural(tcx: TyCtxt<'_>) -> Wrappers {
    let mut out = HashMap::new();
    for ld in tcx.hir_crate_items(()).definitions() {
        let did = ld.to_def_id();
        if !matches!(tcx.def_kind(did), DefKind::Struct) {
            continue;
        }
        if let Some((_, c)) = structural_wrapper(tcx, did) {
            out.insert(did, c);
        }
    }
    out
}

/// Scan local trait impls for the wrapper seam, reading each wrapper's C type
/// from the `type C` associated item.
///
/// The seam trait is the definition of "wrapper" in this codebase:
/// `define_ctype!` expands to an impl carrying `type C`, and the wrappers the
/// macro cannot express -- generic (`OpensslStackOwned<E>`, `Lhash<E>`) or
/// lifetime-carrying (`Packet<'buf>`, `WPacket<'_>`) -- write the same impl by
/// hand. Keying on the trait therefore covers both, and reads the C type from
/// `type C` instead of guessing at field 0.
///
/// `CLayout` is accepted alongside `CCell` so a tree part-way through a
/// migration still resolves; whichever impl carries `type C` is the one read.
fn scan_wrappers(tcx: TyCtxt<'_>) -> HashMap<DefId, DefId> {
    let mut c_ty = HashMap::new();
    for ld in tcx.hir_crate_items(()).definitions() {
        let did = ld.to_def_id();
        if !matches!(tcx.def_kind(did), DefKind::Impl { of_trait: true }) {
            continue;
        }
        let tr = tcx.impl_trait_ref(did).skip_binder();
        let trait_name = tcx.item_name(tr.def_id);
        if !matches!(trait_name.as_str(), "CCell" | "CLayout") {
            continue;
        }
        let ty::TyKind::Adt(sdef, _) = tr.self_ty().kind() else {
            continue;
        };
        for it in tcx.associated_items(did).in_definition_order() {
            if !matches!(tcx.def_kind(it.def_id), DefKind::AssocTy) {
                continue;
            }
            if tcx.item_name(it.def_id).as_str() != "C" {
                continue;
            }
            if let ty::TyKind::Adt(cdef, _) = tcx.type_of(it.def_id).skip_binder().kind() {
                c_ty.insert(sdef.did(), cdef.did());
            }
        }
    }
    c_ty
}

thread_local! {
    /// Built once per compilation (the driver is one rustc invocation per crate).
    static WRAPPERS: std::cell::RefCell<Option<Wrappers>> =
        const { std::cell::RefCell::new(None) };
    static DECLARED: std::cell::RefCell<Option<HashMap<DefId, DefId>>> =
        const { std::cell::RefCell::new(None) };
}

fn with_wrappers<R>(tcx: TyCtxt<'_>, f: impl FnOnce(&Wrappers) -> R) -> R {
    WRAPPERS.with(|c| {
        let mut b = c.borrow_mut();
        if b.is_none() {
            *b = Some(scan_structural(tcx));
        }
        f(b.as_ref().unwrap())
    })
}

/// The `CCell` / `CLayout`-declared set. Read ONLY by
/// `wrapper_newtypes_declared` / `_nonconformant` / `_undeclared`, where the
/// declaration is the subject being measured rather than a dependency.
fn is_declared_wrapper(tcx: TyCtxt<'_>, did: DefId) -> bool {
    DECLARED.with(|c| {
        let mut b = c.borrow_mut();
        if b.is_none() {
            *b = Some(scan_wrappers(tcx));
        }
        b.as_ref().unwrap().contains_key(&did)
    })
}

/// STRUCTURAL wrapper detection, replacing the `CCell`-declared keying.
///
/// A wrapper is a `#[repr(transparent)]` newtype whose single non-ZST field is,
/// after peeling further transparent newtypes, either
///   * a raw pointer / `NonNull` -- a HANDLE (borrowed or owning), or
///   * a `#[repr(C)]` ADT by value -- a LAYOUT newtype over the C object.
///
/// This is what a wrapper IS, in any crate. Keying on `CCell` measured what an
/// author DECLARED, which cannot see a hand-written wrapper (the translator
/// playbook permits them for lifetime-carrying and generic cases) and
/// which ties the audit to ffibox. Every `CCell` wrapper satisfies the
/// structural test by construction -- ffibox requires `#[repr(transparent)]`
/// over `Self::C` -- so the structural set SUBSUMES the declared one,
/// and a type that declares `CCell` while failing this test is a wrapper
/// without the layout it claims: reported as `wrapper_declared_nonconformant`,
/// never silently admitted.
fn peel_transparent<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>) -> Ty<'tcx> {
    let mut cur = t;
    for _ in 0..8 {
        // depth guard; nesting is 2-3 in practice
        // `NonNull<T>` lowers to a PATTERN type (`*const T is !null`), so a
        // handle peeled to the bottom lands here rather than on `RawPtr`.
        if let ty::TyKind::Pat(base, _) = cur.kind() {
            cur = *base;
            continue;
        }
        let ty::TyKind::Adt(def, args) = cur.kind() else {
            return cur;
        };
        if !def.repr().transparent() || !def.is_struct() {
            return cur;
        }
        let mut inner = None;
        for f in def.all_fields() {
            let ft = tcx.type_of(f.did).instantiate(tcx, args).skip_norm_wip();
            if is_phantom(tcx, ft) || is_zst_marker(tcx, ft) {
                continue;
            }
            inner = Some(ft);
            break;
        }
        match inner {
            Some(i) => cur = i,
            None => return cur,
        }
    }
    cur
}

/// `PhantomPinned` and friends: unit-like ZST markers that are not storage.
fn is_zst_marker(tcx: TyCtxt<'_>, t: Ty<'_>) -> bool {
    matches!(t.kind(), ty::TyKind::Adt(d, _)
        if matches!(tcx.item_name(d.did()).as_str(),
                    "PhantomPinned" | "PhantomData"))
}

/// Peel transparent newtypes, then unwrap arrays/slices, to the ADT a field
/// ultimately stores. `[git_oid; 4]` and a layout type over `ffi::git_oid` both
/// land on `git_oid`.
fn field_adt<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>) -> Option<ty::AdtDef<'tcx>> {
    let mut cur = peel_transparent(tcx, t);
    for _ in 0..8 {
        match cur.kind() {
            ty::TyKind::Array(e, _) | ty::TyKind::Slice(e) => {
                cur = peel_transparent(tcx, *e);
            }
            ty::TyKind::Adt(d, _) => return Some(*d),
            _ => return None,
        }
    }
    None
}

/// The C types whose BYTES `did` stores inline, transitively.
///
/// A field is C's when it is a `#[repr(C)]` ADT from ANOTHER CRATE. That
/// cross-crate step is what separates a wrapper from C's own aggregate:
/// `git2::Oid { raw: raw::git_oid }` reaches into libgit2-sys, while
/// `libgit2_sys::git_index_entry { ctime: git_index_time, .. }` matches the
/// same repr shape entirely within its own crate and is not a wrapper of
/// anything. Both are `#[repr(C)]` carrying a `#[repr(C)]` field, so nothing
/// short of the crate boundary tells them apart.
///
/// A same-crate `#[repr(C)]` field is RECURSED into rather than accepted, so a
/// wrapper that reaches C through its own intermediate struct still resolves.
/// Depth- and cycle-guarded.
fn embedded_c(
    tcx: TyCtxt<'_>,
    did: DefId,
    depth: u32,
    seen: &mut HashSet<DefId>,
    out: &mut Vec<DefId>,
) {
    if depth > 8 {
        return;
    }
    for f in tcx.adt_def(did).all_fields() {
        let ft = tcx.type_of(f.did).instantiate_identity().skip_norm_wip();
        if is_phantom(tcx, ft) || is_zst_marker(tcx, ft) {
            continue;
        }
        let Some(d) = field_adt(tcx, ft) else {
            continue;
        };
        if !d.repr().c() {
            continue;
        }
        if d.did().krate != did.krate {
            if !out.contains(&d.did()) {
                out.push(d.did());
            }
        } else if seen.insert(d.did()) {
            embedded_c(tcx, d.did(), depth + 1, seen, out);
        }
    }
}

/// `Some((is_layout, cs))` when `did` is structurally a wrapper. `is_layout` is
/// `true` for a LAYOUT newtype (C's bytes inline), `false` for a HANDLE
/// (pointer). `cs` are the C types it wraps, which the peel already reaches:
///
///   * HANDLE -- the POINTEE. `#[repr(transparent)]` over a raw pointer, or
///     over `NonNull` / `CBorrowedPtr` and friends, which peel to one.
///   * LAYOUT -- every `#[repr(C)]` ADT reached by `embedded_c`. `W` itself
///     must be `#[repr(C)]` or `#[repr(transparent)]`; both give it C's bytes.
///     NOT gated on a single field: a struct carrying a C object beside Rust
///     ones still has those bytes inside it, and `&W` still asserts noalias /
///     readonly / validity across them.
///
/// `cs` is empty for a wrapper naming no ADT (`*mut c_void`).
fn structural_wrapper(tcx: TyCtxt<'_>, did: DefId) -> Option<(bool, Vec<DefId>)> {
    let def = tcx.adt_def(did);
    if !def.is_struct() {
        return None;
    }
    let adt_did = |t: Ty<'_>| match t.kind() {
        ty::TyKind::Adt(d, _) => Some(d.did()),
        _ => None,
    };
    // HANDLE first: a transparent newtype whose storage IS a pointer.
    if def.repr().transparent() {
        let inner = peel_transparent(tcx, tcx.type_of(did).instantiate_identity().skip_norm_wip());
        match inner.kind() {
            ty::TyKind::RawPtr(p, _) | ty::TyKind::Ref(_, p, _) => {
                return Some((false, adt_did(*p).into_iter().collect()));
            }
            ty::TyKind::Adt(d, args) if tcx.item_name(d.did()).as_str() == "NonNull" => {
                // Reached only when the pattern-type peel did not fire; the
                // pointee is the sole type argument.
                return Some((
                    false,
                    args.types().next().and_then(adt_did).into_iter().collect(),
                ));
            }
            _ => {}
        }
    }
    // LAYOUT: C's bytes inline.
    if def.repr().c() || def.repr().transparent() {
        let mut cs = Vec::new();
        let mut seen = HashSet::from([did]);
        embedded_c(tcx, did, 0, &mut seen, &mut cs);
        if !cs.is_empty() {
            return Some((true, cs));
        }
    }
    None
}

/// Is `did` a wrapper type?
fn is_wrapper(tcx: TyCtxt<'_>, did: DefId) -> bool {
    with_wrappers(tcx, |w| w.contains_key(&did))
}

/// The `DefId` of an impl's self-type (`impl T` / `impl Tr for T` -> `T`), via
/// HIR path resolution (no type normalization needed).
fn impl_self_def(tcx: TyCtxt<'_>, impl_did: DefId) -> Option<DefId> {
    let local = impl_did.as_local()?;
    let hir::ItemKind::Impl(imp) = tcx.hir_expect_item(local).kind else {
        return None;
    };
    if let hir::TyKind::Path(hir::QPath::Resolved(_, path)) = imp.self_ty.kind {
        if let hir::def::Res::Def(_, did) = path.res {
            return Some(did);
        }
    }
    None
}

/// True if `did` — or an enclosing item — IS the C-ABI boundary, by either of
/// the two ways a fn can be one:
///
///  * it carries a C symbol name (`#[unsafe(no_mangle)]` / `#[export_name]`),
///    so C callers reach it by that name; or
///  * it has a non-Rust ABI (`extern "C"`), so C reaches it by function
///    pointer — the callback-shim form, which needs no symbol name.
///
/// Both are the port stage's re-export seam: raw and void pointers in such a
/// signature are the C contract (`OPENSSL_sk_freefunc` and friends take
/// type-erased pointers), not a discipline smell, and the unsafe inside belongs
/// to the boundary rather than to the port body.
///
/// The ABI arm was previously a separate `is_extern_c_fn` used ONLY for the
/// pointer-sanctioning sites, so a bare `extern "C"` shim had its pointers
/// excused while its unsafe blocks fell into the unattributed bucket. Folding
/// it in here makes one predicate decide all three.
///
/// Both arms replace an earlier `mod ffi_export` region check: that named a
/// module convention neither ported tree uses, so the sanctioning branch was
/// unreachable and every void pointer fell through to the smell bucket.
fn in_ffi_export(tcx: TyCtxt<'_>, mut did: DefId) -> bool {
    loop {
        if matches!(tcx.def_kind(did), DefKind::Fn | DefKind::AssocFn) {
            let attrs = tcx.codegen_fn_attrs(did);
            if attrs.flags.contains(CodegenFnAttrFlags::NO_MANGLE) || attrs.symbol_name.is_some() {
                return true;
            }
            if tcx.fn_sig(did).skip_binder().skip_binder().abi() != ExternAbi::Rust {
                return true;
            }
        }
        match tcx.opt_parent(did) {
            // Keep walking out of closures / nested bodies into the owning fn;
            // stop at the module boundary.
            Some(p) if !matches!(tcx.def_kind(p), DefKind::Mod | DefKind::ForeignMod) => did = p,
            _ => return false,
        }
    }
}

/// True if `did` is (transitively) inside ANY `impl`/`trait` body (an accessor
/// *definition* — the sanctioned home for raw field projection).
fn in_any_impl(tcx: TyCtxt<'_>, mut did: DefId) -> bool {
    while let Some(parent) = tcx.opt_parent(did) {
        match tcx.def_kind(parent) {
            DefKind::Impl { .. } | DefKind::Trait => return true,
            DefKind::Mod | DefKind::ForeignMod => return false,
            _ => did = parent,
        }
    }
    false
}

/// True if `did` is (transitively) inside an `impl T { .. }` / `impl Tr for T`
/// whose `T` is a wrapper (implements `CCell`).
fn in_wrapper_impl(tcx: TyCtxt<'_>, mut did: DefId) -> bool {
    while let Some(parent) = tcx.opt_parent(did) {
        match tcx.def_kind(parent) {
            DefKind::Impl { .. } => {
                return impl_self_def(tcx, parent).is_some_and(|s| is_wrapper(tcx, s));
            }
            DefKind::Mod | DefKind::ForeignMod => return false,
            _ => did = parent,
        }
    }
    false
}

#[derive(Default)]
struct Counts {
    unsafe_blocks: u64,
    unsafe_block_stmts: u64,
    unsafe_block_lines: u64, // raw brace-to-brace span (incl. blanks/comments)
    unsafe_block_code_lines: u64, // non-blank, non-`//`-comment lines only
    unsafe_blocks_wrapper_impl: u64, // unsafe blocks inside `impl <wrapper T>`
    unsafe_blocks_ffi_export: u64,
    // `unsafe fn` / `unsafe impl` / `unsafe trait` DECLARATIONS. A block is a
    // local assertion its author discharges; an `unsafe fn` pushes the
    // obligation onto every caller, and a `pub` one exports it out of the
    // crate. Same sanctioning axis as everything else: the seam names and the
    // C-ABI gateway are expected, the remainder is the finding.
    // A partition: unsafe_fns = seam + pub_smell + priv_smell. "pub" is rustc's
    // effective visibility: callable from outside the crate (a trait-impl method
    // reachable through a public trait and type counts; a `pub` item in a
    // private module does not).
    unsafe_fns: u64,
    unsafe_fns_seam: u64,
    unsafe_fns_pub_smell: u64,
    unsafe_fns_priv_smell: u64,
    unsafe_impls: u64,
    unsafe_traits: u64,
    // Calls to a foreign item -- one declared in an `extern` block
    // (`is_foreign_item`), which is the FFI boundary itself and is
    // crate-agnostic: a bindgen `*-sys` binding, `libc`, or a local
    // `extern "C"` block all resolve to it. Calling one is an unsafe op, so
    // this is the crate-wide unsafe-FFI-call surface. Resolution-based on the
    // callee, so alias- and re-export-proof.
    ffi_calls: u64,
    // Wrapper inventory. `wrapper_newtypes` is the STRUCTURAL count -- every
    // `#[repr(transparent)]` newtype over a pointer or a `#[repr(C)]` type --
    // split into the two roles. The `_declared` pair is the `CCell` baseline
    // this replaces, kept so the two can be compared: `_nonconformant` is a
    // type declaring `CCell` that fails the structural test, i.e. a wrapper
    // without the layout it claims, and `_undeclared` is one the old keying
    // could not see.
    wrapper_newtypes: u64,
    wrapper_newtypes_declared: u64,
    wrapper_declared_nonconformant: u64,
    wrapper_newtypes_undeclared: u64, // unsafe blocks at the C-ABI boundary
    //   (`in_ffi_export`: `#[no_mangle]` /
    //   `#[export_name]` / `extern "C"`)
    // Signature raw pointers. ONE family, with the sanctioned subset named
    // rather than excluded: `raw_ptr_args` + `raw_ptr_rets` is every raw-pointer position
    // in a signature (the denominator), `raw_ptr_seam` the subset that is legitimate
    // by construction, so the smell is `raw_ptr_args + raw_ptr_rets - raw_ptr_seam`. The old
    // scheme split `rp_wrap_nonseam_*` from `rp_outside_*` and counted the seam
    // region in NEITHER, so it reported a numerator with no denominator.
    raw_ptr_args: u64,
    raw_ptr_rets: u64,
    raw_ptr_seam: u64,       // seam fn / C-ABI boundary / ptr-to-own-Self
    raw_ptr_wrapped: u64,    // of the NON-seam remainder, pointee is a wrapped C type
    // the NON-seam remainder, split by the declaring fn's effective visibility:
    // raw_ptr_args + raw_ptr_rets = raw_ptr_seam + raw_ptr_pub_smell + raw_ptr_priv_smell
    raw_ptr_pub_smell: u64,
    raw_ptr_priv_smell: u64,
    // `&W` / `&mut W` (incl. the receiver), W a layout newtype, partitioned:
    // sanctioned (REF_ACCESSORS / STD_VALUE_TRAITS impls) + smell (the rest)
    ref_to_type_wrapper_sanctioned: u64,
    ref_to_type_wrapper_smell: u64,
    // in function BODIES: a `&W` / `&mut W` (or `&[W]`, `Option<&W>`, ..) formed
    // from a raw pointer -- `&*p`, `&(*p).f`, an autoref through `*p`, or a
    // non-local call such as `p.as_ref()` / `NonNull::as_ref` /
    // `slice::from_raw_parts`. Never sanctioned: target 0.
    ref_to_type_wrapper_body_smell: u64,
    // `impl Deref` / `impl DerefMut` (core) whose Self is a wrapper, layout or
    // handle. Never sanctioned: target 0.
    deref_impl_on_wrapper: u64,
    // raw-pointer positions in the fields of structs/unions the crate declares
    // (generated bindings excluded); classified into raw_ptr_seam / _pub_smell /
    // _priv_smell with the signature positions
    raw_ptr_fields: u64,
    // `(*p).field` where `p: *C` and `C` has a wrapper (bypasses the
    // accessor): total, and the subset outside any impl/trait (the smell).
    field_proj_wrapped: u64,
    field_proj_outside_impl: u64,
    // `&(*p).field` / `&mut (*p).field` where `p: *C` and `C` has a wrapper --
    // a reference one level down into memory C may write. Should be 0.
    field_ref_wrapped: u64,
    // `*c_void` in signatures, a subset of the raw-pointer positions, partitioned
    // the same way: seam (seam fn / ffi_export) + pub smell + private smell
    void_ptr_seam: u64,
    void_ptr_pub_smell: u64,
    void_ptr_priv_smell: u64,
    raw_ptr_derefs: u64,
    raw_ptr_derefs_outside_impl: u64, // ...of those, the subset NOT in any impl/trait body
    total_stmts: u64,
    code_lines: u64, // crate-wide physical LoC: non-blank, non-`//`-comment source lines
}

/// Source sites `(file, 1-based line)` per counter, keyed by the counter's
/// output name: every increment of a location-counting counter records where it
/// happened. Line and statement totals have none. Aggregated by `sites_json`.
#[derive(Default)]
struct Sites(std::collections::BTreeMap<&'static str, Vec<(String, usize)>>);

impl Sites {
    fn add(&mut self, counter: &'static str, site: (String, usize)) {
        self.0.entry(counter).or_default().push(site);
    }

    /// `{"<counter>": [{"file":..,"count":N,"lines":[..]}], ..}`, where `count`
    /// is the number of increments in the file (so a counter's per-file counts
    /// sum to the counter) and `lines` the distinct lines they fell on.
    fn json(&self) -> String {
        use std::collections::BTreeMap;
        let rows: Vec<String> = self
            .0
            .iter()
            .map(|(k, v)| {
                let mut by_file: BTreeMap<&str, Vec<usize>> = BTreeMap::new();
                for (f, l) in v {
                    by_file.entry(f.as_str()).or_default().push(*l);
                }
                let files: Vec<String> = by_file
                    .iter()
                    .map(|(f, ls)| {
                        let mut u = ls.clone();
                        u.sort_unstable();
                        u.dedup();
                        let arr: Vec<String> = u.iter().map(|l| l.to_string()).collect();
                        format!(
                            "{{\"file\":\"{}\",\"count\":{},\"lines\":[{}]}}",
                            f,
                            ls.len(),
                            arr.join(",")
                        )
                    })
                    .collect();
                format!("\"{}\":[{}]", k, files.join(","))
            })
            .collect();
        format!("{{{}}}", rows.join(","))
    }
}

/// `span_site` for a counter site: a span produced by a macro (`define_ctype!`,
/// a `#[derive]`) is mapped to the invocation in this crate, so the site names
/// the line the author wrote rather than a line of the macro's own source.
fn counter_site(tcx: TyCtxt<'_>, span: Span) -> (String, usize) {
    span_site(tcx, span.source_callsite())
}

/// `(file, 1-based line)` for a span, local-path filename.
fn span_site(tcx: TyCtxt<'_>, span: Span) -> (String, usize) {
    let sm = tcx.sess.source_map();
    let file = sm
        .span_to_filename(span)
        .into_local_path()
        .map(|p| p.display().to_string())
        .unwrap_or_default();
    let line = sm.lookup_char_pos(span.lo()).line;
    (file, line)
}

/// Aggregate `(file, line)` sites into audit.py's
/// `[{"file":..,"count":N,"lines":[..]}]` JSON (one row per file, lines sorted/deduped).
fn sites_json(sites: &[(String, usize)]) -> String {
    use std::collections::BTreeMap;
    let mut by_file: BTreeMap<&str, Vec<usize>> = BTreeMap::new();
    for (f, l) in sites {
        by_file.entry(f.as_str()).or_default().push(*l);
    }
    let rows: Vec<String> = by_file
        .iter()
        .map(|(f, lines)| {
            let mut ls = lines.clone();
            ls.sort_unstable();
            ls.dedup();
            let arr: Vec<String> = ls.iter().map(|l| l.to_string()).collect();
            format!(
                "{{\"file\":\"{}\",\"count\":{},\"lines\":[{}]}}",
                f,
                ls.len(),
                arr.join(",")
            )
        })
        .collect();
    format!("[{}]", rows.join(","))
}

struct BodyVisitor<'a, 'tcx> {
    tcx: TyCtxt<'tcx>,
    typeck: &'tcx TypeckResults<'tcx>,
    depth: u32,       // unsafe-block nesting depth
    in_wrapper: bool, // this body is inside an `impl <wrapper T>`
    in_ffi: bool,     // this body IS / is inside the C-ABI boundary
    in_impl: bool,    // this body is inside any impl/trait
    wrapped_c: &'a HashSet<DefId>,
    c: &'a mut Counts,
    sites: &'a mut Sites,
}

impl<'a, 'tcx> BodyVisitor<'a, 'tcx> {
    /// Is `e` a place reached through a raw-pointer dereference (`*p`,
    /// `(*p).f`, `(*p)[i]`)?
    fn raw_based_place(&self, mut e: &'tcx hir::Expr<'tcx>) -> bool {
        loop {
            match e.kind {
                hir::ExprKind::Field(base, _) | hir::ExprKind::Index(base, _, _) => e = base,
                hir::ExprKind::Unary(hir::UnOp::Deref, inner) => {
                    return self.typeck.expr_ty_adjusted(inner).is_raw_ptr();
                }
                _ => return false,
            }
        }
    }

    fn body_ref(&mut self, e: &'tcx hir::Expr<'tcx>) {
        self.c.ref_to_type_wrapper_body_smell += 1;
        self.sites
            .add("ref_to_type_wrapper_body_smell", counter_site(self.tcx, e.span));
    }

    /// Count a reference to a layout newtype formed from a raw pointer at `e`.
    fn count_body_refs(&mut self, e: &'tcx hir::Expr<'tcx>) {
        let tcx = self.tcx;
        match e.kind {
            // `&*p`, `&mut *p`, `&(*p).f`
            hir::ExprKind::AddrOf(hir::BorrowKind::Ref, _, operand)
                if is_ref_to_type_wrapper(tcx, self.typeck.expr_ty(e))
                    && self.raw_based_place(operand) =>
            {
                self.body_ref(e);
                return;
            }
            // a non-local call from a raw pointer / NonNull to a reference
            hir::ExprKind::Call(f, args) => {
                let callee = match self.typeck.expr_ty(f).kind() {
                    ty::TyKind::FnDef(did, _) => Some(*did),
                    _ => None,
                };
                if callee.is_some_and(|d| !d.is_local())
                    && contains_ref_to_type_wrapper(tcx, self.typeck.expr_ty(e))
                    && args.iter().any(|a| is_raw_or_non_null(tcx, self.typeck.expr_ty_adjusted(a)))
                {
                    self.body_ref(e);
                    return;
                }
            }
            hir::ExprKind::MethodCall(_, recv, args, _) => {
                let callee = self.typeck.type_dependent_def_id(e.hir_id);
                if callee.is_some_and(|d| !d.is_local())
                    && contains_ref_to_type_wrapper(tcx, self.typeck.expr_ty(e))
                    && std::iter::once(recv)
                        .chain(args.iter())
                        .any(|a| is_raw_or_non_null(tcx, self.typeck.expr_ty(a)))
                {
                    self.body_ref(e);
                    return;
                }
            }
            _ => {}
        }
        // an autoref through `*p`: `(*p).method()` with `&self` on the wrapper
        if self.raw_based_place(e) {
            let borrows = self.typeck.expr_adjustments(e).iter().any(|a| {
                matches!(a.kind, rustc_middle::ty::adjustment::Adjust::Borrow(_))
                    && is_ref_to_type_wrapper(tcx, a.target)
            });
            if borrows {
                self.body_ref(e);
            }
        }
    }
}

impl<'a, 'tcx> Visitor<'tcx> for BodyVisitor<'a, 'tcx> {
    fn visit_stmt(&mut self, s: &'tcx hir::Stmt<'tcx>) {
        self.c.total_stmts += 1;
        if self.depth > 0 {
            self.c.unsafe_block_stmts += 1;
        }
        intravisit::walk_stmt(self, s);
    }

    fn visit_expr(&mut self, e: &'tcx hir::Expr<'tcx>) {
        self.count_body_refs(e);
        match e.kind {
            // `unsafe { ... }`
            hir::ExprKind::Block(b, _)
                if matches!(b.rules, hir::BlockCheckMode::UnsafeBlock(_)) =>
            {
                self.c.unsafe_blocks += 1;
                self.sites.add("unsafe_blocks", counter_site(self.tcx, e.span));
                if self.in_wrapper {
                    // Region attribution only. Where the block's TEXT came from
                    // does not change what it is: an unsafe block in a wrapper
                    // impl is an unsafe block in a wrapper impl.
                    self.c.unsafe_blocks_wrapper_impl += 1;
                    self.sites.add("unsafe_blocks_wrapper_impl", counter_site(self.tcx, e.span));
                }
                if self.in_ffi {
                    self.c.unsafe_blocks_ffi_export += 1;
                    self.sites.add("unsafe_blocks_ffi_export", counter_site(self.tcx, e.span));
                }
                // Line metrics: outermost blocks only (nested ones would
                // double-count). EVERY outermost block counts, macro-expanded
                // or not: the metric asks how much unsafe is compiled into this
                // crate, and a block ffibox's `define_ctype!` emitted runs here
                // exactly like one an agent typed. Sanctioning is the only axis
                // that excuses anything, and it does not apply to blocks --
                // `unsafe_blocks_wrapper_impl` / `_ffi_export` ATTRIBUTE a block
                // to a region, they do not exempt it.
                //
                // The earlier exclusion was justified by `span_to_snippet` being
                // unable to reach a macro span's text; that is not so -- every
                // macro-expanded block on libippcp resolves -- and dropping them
                // understated the ratio in proportion to how macro-driven the
                // wrapping is (7.28% against 10.01% here), which is the same bias
                // the `code_lines` rebuild removed from the denominator.
                if self.depth == 0 {
                    let sm = self.tcx.sess.source_map();
                    let lo = sm.lookup_char_pos(b.span.lo()).line;
                    let hi = sm.lookup_char_pos(b.span.hi()).line;
                    self.c.unsafe_block_lines += (hi.saturating_sub(lo) + 1) as u64;
                    // filtered: drop blank + `//`-comment lines (same filter as
                    // the code_LOC denominator, so the ratio is apples-to-apples)
                    if let Ok(snip) = sm.span_to_snippet(b.span) {
                        self.c.unsafe_block_code_lines +=
                            snip.lines()
                                .filter(|l| {
                                    let t = l.trim();
                                    !t.is_empty() && !t.starts_with("//")
                                })
                                .count() as u64;
                    }
                }
                self.depth += 1;
                intravisit::walk_expr(self, e);
                self.depth -= 1;
                return;
            }
            // `*operand` where operand is a raw pointer (type-decided)
            hir::ExprKind::Unary(hir::UnOp::Deref, inner) => {
                if self.typeck.expr_ty(inner).is_raw_ptr() {
                    self.c.raw_ptr_derefs += 1;
                    self.sites.add("raw_ptr_derefs", counter_site(self.tcx, e.span));
                    // The actionable split: derefs in wrapper accessor / seam
                    // bodies (inside an impl) are the sanctioned centralisation;
                    // those outside any impl are port-body raw access.
                    if !self.in_impl {
                        self.c.raw_ptr_derefs_outside_impl += 1;
                        self.sites.add("raw_ptr_derefs_outside_impl", counter_site(self.tcx, e.span));
                    }
                }
            }
            // `(*p).field` where `p: *C` and `C` has a wrapper (also covers the
            // `addr_of!((*p).field)` form, whose operand IS this field expr).
            hir::ExprKind::Field(base, _) => {
                if let hir::ExprKind::Unary(hir::UnOp::Deref, inner) = base.kind {
                    if let ty::TyKind::RawPtr(pointee, _) = self.typeck.expr_ty(inner).kind() {
                        if pointee_has_wrapper(self.tcx, *pointee, self.wrapped_c) {
                            self.c.field_proj_wrapped += 1;
                            self.sites.add("field_proj_wrapped", counter_site(self.tcx, e.span));
                            if !self.in_impl {
                                self.c.field_proj_outside_impl += 1;
                                self.sites.add("field_proj_outside_impl", counter_site(self.tcx, e.span));
                            }
                        }
                    }
                }
            }
            // `&(*p).field` / `&mut (*p).field` where `p: *C` and `C` has a
            // wrapper: a reference over a FIELD of memory C may write -- the
            // same rule that keeps `&W` out, one level down. `addr_of!` /
            // `&raw` lower to `BorrowKind::Raw`, so matching only
            // `BorrowKind::Ref` is exactly the sanctioned/forbidden split.
            hir::ExprKind::AddrOf(hir::BorrowKind::Ref, _, operand) => {
                if let hir::ExprKind::Field(base, _) = operand.kind {
                    if let hir::ExprKind::Unary(hir::UnOp::Deref, inner) = base.kind {
                        if let ty::TyKind::RawPtr(pointee, _) = self.typeck.expr_ty(inner).kind() {
                            if pointee_has_wrapper(self.tcx, *pointee, self.wrapped_c) {
                                self.c.field_ref_wrapped += 1;
                                self.sites.add("field_ref_wrapped", counter_site(self.tcx, e.span));
                            }
                        }
                    }
                }
            }
            _ => {}
        }
        intravisit::walk_expr(self, e);
    }
}

/// The `ffibox` macros, tallied by expansion site. `define_ctype!` emits the
/// layout type and its handles; the `impl_*!` family binds a C lifecycle or
/// lock routine to a policy (or, for `impl_cguarded!`, to the layout type).
const FFIBOX_MACROS: &[&str] = &[
    "define_ctype",
    "impl_cdrop",
    "impl_cdrop_str",
    "impl_cdrop_void",
    "impl_cdupclone",
    "impl_cdupclone_str",
    "impl_crefclone",
    "impl_clendrop",
    "impl_clenclone",
    "impl_cdispose",
    "impl_cguarded",
];

/// The crate whose primitives `UM_MODE=usage` profiles.
fn is_ffibox_crate(tcx: TyCtxt<'_>, did: DefId) -> bool {
    tcx.crate_name(did.krate).as_str() == "ffibox"
}

/// Recursively tally references to ffibox structs in a type.
fn count_ty(tcx: TyCtxt<'_>, t: Ty<'_>, m: &mut std::collections::BTreeMap<String, u64>) {
    match t.kind() {
        ty::TyKind::Adt(def, args) => {
            let did = def.did();
            if is_ffibox_crate(tcx, did) {
                *m.entry(tcx.item_name(did).to_string()).or_default() += 1;
            }
            for a in args.types() {
                count_ty(tcx, a, m);
            }
        }
        ty::TyKind::RawPtr(p, _) | ty::TyKind::Ref(_, p, _) => count_ty(tcx, *p, m),
        ty::TyKind::Slice(e) | ty::TyKind::Array(e, _) => count_ty(tcx, *e, m),
        _ => {}
    }
}

/// `UM_MODE=usage`: profile ffibox primitive usage.
///  - `types`: references to the owner / handle / view structs in type positions
///    (fn signatures, struct/enum/union fields, const/alias types)
///  - `trait_impls`: `impl <ffibox trait> for T` counts
///  - `macros`: distinct invocations of the ffibox `*!` macros
///  - `ffi_calls`: per-`crate::symbol` count of every call to a foreign fn
///    (`tcx.is_foreign_item` — declared in an `extern` block), crate-agnostic
///    (bindgen `*-sys`, `libc`, local `extern "C"`). Calling one is unsafe, so
///    this is the crate-wide unsafe-FFI-call surface.
///  - `ffi_call_sites`: those calls grouped `{crate::symbol: {region: [{file,count,lines}]}}`
///    where region is `free_fn` / `inherent_impl` / `trait_impl:<Trait>` — so a
///    `git__free` in `trait_impl:CDrop` (a sanctioned wrapper dtor) is separable
///    from one in a `free_fn` port body (actionable smell)
fn usage_json(tcx: TyCtxt<'_>, krate: rustc_span::Symbol) -> String {
    use std::collections::BTreeMap;
    let mut types: BTreeMap<String, u64> = BTreeMap::new();
    let mut trait_impls: BTreeMap<String, u64> = BTreeMap::new();
    let mut macros: BTreeMap<String, HashSet<rustc_span::ExpnId>> = BTreeMap::new();
    // Crate-wide scan: every call to a foreign fn — one declared in an `extern`
    // block (`tcx.is_foreign_item`), which is the FFI boundary itself and is
    // crate-agnostic (bindgen `*-sys`, `libc`, or a local `extern "C"` block all
    // resolve to it). Calling one is an unsafe op, so this is the unsafe-FFI-call
    // surface. Resolution-based (callee `DefId`), so alias-/re-export-proof and
    // multi-line-safe. Keyed `crate::symbol` so same-named foreign fns from
    // different crates (e.g. `libc::close` vs a sys binding) stay distinct.
    let mut ffi_calls: BTreeMap<String, u64> = BTreeMap::new();
    // crate::symbol -> region ("free_fn" | "inherent_impl" | "trait_impl:<Trait>")
    // -> sites. The region separates wrapper-teardown chokepoints (a `git__free`
    // in `trait_impl:CDrop` / `:CLenDrop`) from port-body smell (`free_fn` /
    // `inherent_impl`), so the actionable subset is a filter, not a judgement.
    let mut ffi_sites: BTreeMap<String, BTreeMap<String, Vec<(String, usize)>>> = BTreeMap::new();
    for owner in tcx.hir_body_owners() {
        let region = call_region(tcx, owner.to_def_id());
        let typeck = tcx.typeck(owner);
        let mut callees: Vec<(DefId, rustc_span::Span)> = Vec::new();
        CallCollector {
            typeck,
            out: &mut callees,
        }
        .visit_body(tcx.hir_body_owned_by(owner));
        for (did, sp) in callees {
            if tcx.is_foreign_item(did) {
                let key = format!("{}::{}", tcx.crate_name(did.krate), tcx.item_name(did));
                *ffi_calls.entry(key.clone()).or_default() += 1;
                ffi_sites
                    .entry(key)
                    .or_default()
                    .entry(region.clone())
                    .or_default()
                    .push(span_site(tcx, sp));
            }
        }
    }

    for ld in tcx.hir_crate_items(()).definitions() {
        let did = ld.to_def_id();
        match tcx.def_kind(did) {
            DefKind::Fn | DefKind::AssocFn => {
                let sig = tcx.fn_sig(did).skip_binder().skip_binder();
                for t in sig
                    .inputs()
                    .iter()
                    .copied()
                    .chain(std::iter::once(sig.output()))
                {
                    count_ty(tcx, t, &mut types);
                }
            }
            DefKind::Struct | DefKind::Enum | DefKind::Union => {
                for f in tcx.adt_def(did).all_fields() {
                    count_ty(tcx, tcx.type_of(f.did).skip_binder(), &mut types);
                }
            }
            DefKind::Impl { of_trait: true } => {
                let tdid = tcx.impl_trait_ref(did).skip_binder().def_id;
                if is_ffibox_crate(tcx, tdid) {
                    *trait_impls
                        .entry(tcx.item_name(tdid).to_string())
                        .or_default() += 1;
                }
            }
            _ => {}
        }
        // distinct macro invocations (items from one invocation share an ExpnId)
        let ctxt = tcx.def_span(did).ctxt();
        if let ExpnKind::Macro(MacroKind::Bang, name) = ctxt.outer_expn_data().kind {
            if let Some(last) = name.as_str().rsplit("::").next() {
                if FFIBOX_MACROS.contains(&last) {
                    macros
                        .entry(last.to_string())
                        .or_default()
                        .insert(ctxt.outer_expn());
                }
            }
        }
    }

    let obj = |m: &BTreeMap<String, u64>| {
        m.iter()
            .map(|(k, v)| format!("\"{k}\":{v}"))
            .collect::<Vec<_>>()
            .join(",")
    };
    let macros_obj = macros
        .iter()
        .map(|(k, s)| format!("\"{k}\":{}", s.len()))
        .collect::<Vec<_>>()
        .join(",");
    let ffi_sites_obj = ffi_sites
        .iter()
        .map(|(sym, by_region)| {
            let inner = by_region
                .iter()
                .map(|(region, sites)| format!("\"{region}\":{}", sites_json(sites)))
                .collect::<Vec<_>>()
                .join(",");
            format!("\"{sym}\":{{{}}}", inner)
        })
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "{{\"crate\":\"{krate}\",\"types\":{{{}}},\"trait_impls\":{{{}}},\"macros\":{{{}}},\"ffi_calls\":{{{}}},\"ffi_call_sites\":{{{}}}}}",
        obj(&types), obj(&trait_impls), macros_obj, obj(&ffi_calls), ffi_sites_obj
    )
}

// ---------------------------------------------------------------- seed mode

fn enclosing_impl_self(tcx: TyCtxt<'_>, mut did: DefId) -> Option<DefId> {
    while let Some(parent) = tcx.opt_parent(did) {
        match tcx.def_kind(parent) {
            DefKind::Impl { .. } => return impl_self_def(tcx, parent),
            DefKind::Mod | DefKind::ForeignMod => return None,
            _ => did = parent,
        }
    }
    None
}

/// Classify a body owner's enclosing region, for grouping ffi-call sites:
/// `trait_impl:<Trait>` (a call inside `impl Trait for T` — e.g. the
/// `CDrop` / `CLenDrop` wrapper-teardown chokepoints), `inherent_impl`
/// (a method in `impl T { .. }`), or `free_fn` (a free function or any
/// other body not in an impl).
fn call_region(tcx: TyCtxt<'_>, mut did: DefId) -> String {
    while let Some(parent) = tcx.opt_parent(did) {
        match tcx.def_kind(parent) {
            DefKind::Impl { of_trait } => {
                return if of_trait {
                    let tdid = tcx.impl_trait_ref(parent).skip_binder().def_id;
                    format!("trait_impl:{}", tcx.item_name(tdid))
                } else {
                    "inherent_impl".to_string()
                };
            }
            DefKind::Mod | DefKind::ForeignMod => break,
            _ => did = parent,
        }
    }
    "free_fn".to_string()
}

/// Collect free-function callee `DefId`s + call-site spans in a body, for FFI
/// call classification and named-symbol resolution.
struct CallCollector<'a, 'tcx> {
    typeck: &'tcx TypeckResults<'tcx>,
    out: &'a mut Vec<(DefId, Span)>,
}
impl<'a, 'tcx> Visitor<'tcx> for CallCollector<'a, 'tcx> {
    fn visit_expr(&mut self, e: &'tcx hir::Expr<'tcx>) {
        if let hir::ExprKind::Call(f, _) = e.kind {
            if let hir::ExprKind::Path(ref qp) = f.kind {
                if let hir::def::Res::Def(_, did) = self.typeck.qpath_res(qp, f.hir_id) {
                    self.out.push((did, e.span));
                }
            }
        }
        intravisit::walk_expr(self, e);
    }
}

struct MetricsCallbacks;

impl Callbacks for MetricsCallbacks {
    fn after_analysis(
        &mut self,
        _compiler: &rustc_interface::interface::Compiler,
        tcx: TyCtxt<'_>,
    ) -> Compilation {
        let krate = tcx.crate_name(rustc_span::def_id::LOCAL_CRATE);
        // Under cargo, only emit for workspace primary packages (skips deps and
        // build scripts); standalone (run.sh) always emits.
        let under_cargo = std::env::var_os("CARGO").is_some();
        let primary = std::env::var_os("CARGO_PRIMARY_PACKAGE").is_some();
        if under_cargo && (!primary || krate.as_str() == "build_script_build") {
            return Compilation::Continue;
        }
        // Usage mode: primitive-usage profile, separate from the unsafe metrics.
        if std::env::var("UM_MODE").as_deref() == Ok("usage") {
            println!("{}", usage_json(tcx, krate));
            return Compilation::Continue;
        }
        // Named mode prints its site entries, then falls through to emit the
        // crate-wide metrics block from the same compilation. The dispatcher
        // merges both stdout lines per crate.
        if std::env::var_os("UM_DEBUG").is_some() {
            let (mut ns, mut nw, mut shown) = (0u32, 0u32, 0u32);
            for ld in tcx.hir_crate_items(()).definitions() {
                let did = ld.to_def_id();
                if matches!(tcx.def_kind(did), DefKind::Struct) {
                    ns += 1;
                    let nm = match tcx.def_span(did).ctxt().outer_expn_data().kind {
                        ExpnKind::Macro(_, s) => s.to_string(),
                        k => format!("{k:?}"),
                    };
                    if is_wrapper(tcx, did) {
                        nw += 1;
                    }
                    if shown < 10 {
                        eprintln!("  STRUCT {} expn={}", tcx.item_name(did), nm);
                        shown += 1;
                    }
                }
            }
            eprintln!("CRATE structs={ns} detected_wrappers={nw}");
        }
        // Set of C types that have a wrapper (a safe wrapper exists). Each
        // wrapper contributes its seam's `type C`, either representation.
        let wrapped_c: HashSet<DefId> =
            with_wrappers(tcx, |w| w.values().flatten().copied().collect());

        let mut c = Counts::default();
        let mut sites = Sites::default();
        // Every body owner (fn, closure, const/static initializer, ...). Each is
        // a separate typeck context; intravisit does not descend into nested
        // bodies, so visiting every owner covers the whole crate exactly once.
        // Declaration-shaped metrics need their own pass: `hir_body_owners()`
        // yields only fns, closures and initializers, so a struct / impl /
        // trait never reaches it.
        for ld in tcx.hir_crate_items(()).definitions() {
            let did = ld.to_def_id();
            if matches!(tcx.def_kind(did), DefKind::Struct | DefKind::Union) {
                count_raw_ptr_fields(tcx, did, &wrapped_c, &mut c, &mut sites);
            }
            match tcx.def_kind(did) {
                DefKind::Struct => {
                    let is_layout = matches!(structural_wrapper(tcx, did), Some((true, _)));
                    let declared = is_declared_wrapper(tcx, did);
                    // LAYOUT newtypes only. A handle is a wrapper too, but it
                    // is not the set this audit polices: `&handle` covers
                    // Rust-owned pointer storage and is ordinary, while `&W` on
                    // a layout newtype is the hazard `ref_to_type_wrapper`
                    // exists to keep at 0.
                    if is_layout {
                        c.wrapper_newtypes += 1;
                        sites.add("wrapper_newtypes", counter_site(tcx, tcx.def_span(did)));
                        if !declared {
                            c.wrapper_newtypes_undeclared += 1;
                            sites.add("wrapper_newtypes_undeclared", counter_site(tcx, tcx.def_span(did)));
                        }
                    }
                    if declared {
                        c.wrapper_newtypes_declared += 1;
                        sites.add("wrapper_newtypes_declared", counter_site(tcx, tcx.def_span(did)));
                        if !is_layout {
                            c.wrapper_declared_nonconformant += 1;
                            sites.add("wrapper_declared_nonconformant", counter_site(tcx, tcx.def_span(did)));
                        }
                    }
                }
                DefKind::Impl { of_trait: true } => {
                    // `TrivialClone` is a compiler-internal marker `#[derive(Clone)]`
                    // emits as an `unsafe impl`; it asserts nothing the author
                    // wrote and would swamp the real lifecycle contracts.
                    let internal = tcx
                        .item_name(tcx.impl_trait_ref(did).skip_binder().def_id)
                        .as_str()
                        == "TrivialClone";
                    if !internal && tcx.impl_trait_header(did).safety.is_unsafe() {
                        c.unsafe_impls += 1;
                        sites.add("unsafe_impls", counter_site(tcx, tcx.def_span(did)));
                    }
                    // `Deref` / `DerefMut` on a wrapper (layout or handle) turns
                    // every `*w` and auto-deref into a reference to whatever it
                    // targets -- typically the C object -- outside the handles.
                    let tr = tcx.impl_trait_ref(did).skip_binder().def_id;
                    if tcx.crate_name(tr.krate).as_str() == "core"
                        && matches!(tcx.item_name(tr).as_str(), "Deref" | "DerefMut")
                    {
                        let self_ty = tcx.type_of(did).instantiate_identity().skip_norm_wip();
                        if let ty::TyKind::Adt(d, _) = self_ty.kind() {
                            if is_wrapper(tcx, d.did()) {
                                c.deref_impl_on_wrapper += 1;
                                sites.add("deref_impl_on_wrapper", counter_site(tcx, tcx.def_span(did)));
                            }
                        }
                    }
                }
                DefKind::Trait => {
                    if tcx.trait_def(did).safety.is_unsafe() {
                        c.unsafe_traits += 1;
                        sites.add("unsafe_traits", counter_site(tcx, tcx.def_span(did)));
                    }
                }
                _ => {}
            }
        }

        for owner in tcx.hir_body_owners() {
            let did = owner.to_def_id();
            {
                let typeck = tcx.typeck(owner);
                let mut callees: Vec<(DefId, Span)> = Vec::new();
                CallCollector {
                    typeck,
                    out: &mut callees,
                }
                .visit_body(tcx.hir_body_owned_by(owner));
                for (_, span) in callees.iter().filter(|(d, _)| tcx.is_foreign_item(*d)) {
                    c.ffi_calls += 1;
                    sites.add("ffi_calls", counter_site(tcx, *span));
                }
            }
            let in_wrapper = in_wrapper_impl(tcx, did);
            let in_ffi = in_ffi_export(tcx, did);
            let exported = did.as_local().is_some_and(|l| tcx.effective_visibilities(()).is_exported(l));
            let in_impl = in_any_impl(tcx, did);
            {
                let typeck = tcx.typeck(owner);
                let body = tcx.hir_body_owned_by(owner);
                let mut v = BodyVisitor {
                    tcx,
                    typeck,
                    depth: 0,
                    in_wrapper,
                    in_ffi,
                    in_impl,
                    wrapped_c: &wrapped_c,
                    c: &mut c,
                    sites: &mut sites,
                };
                v.visit_body(body);
            }
            // Signature analysis (fns only).
            if matches!(tcx.def_kind(did), DefKind::Fn | DefKind::AssocFn) {
                let sig = tcx.fn_sig(did).skip_binder().skip_binder();
                let seam = is_seam_fn(tcx, did);
                // `&mut <wrapper>` and `*c_void` anywhere in the signature.
                for t in sig
                    .inputs()
                    .iter()
                    .copied()
                    .chain(std::iter::once(sig.output()))
                {
                    if is_ref_to_type_wrapper(tcx, t) {
                        let site = counter_site(tcx, tcx.def_span(did));
                        if ref_to_wrapper_sanctioned(tcx, did) {
                            c.ref_to_type_wrapper_sanctioned += 1;
                            sites.add("ref_to_type_wrapper_sanctioned", site);
                        } else {
                            c.ref_to_type_wrapper_smell += 1;
                            sites.add("ref_to_type_wrapper_smell", site);
                        }
                    }
                    let mut pointees = Vec::new();
                    raw_pointees(tcx, t, &mut pointees);
                    for _ in pointees.iter().filter(|p| is_c_void(tcx, **p)) {
                        let site = counter_site(tcx, tcx.def_span(did));
                        if seam || in_ffi {
                            c.void_ptr_seam += 1;
                            sites.add("void_ptr_seam", site);
                        } else if exported {
                            c.void_ptr_pub_smell += 1;
                            sites.add("void_ptr_pub_smell", site);
                        } else {
                            c.void_ptr_priv_smell += 1;
                            sites.add("void_ptr_priv_smell", site);
                        }
                    }
                }
                // `unsafe fn` DECLARATIONS. Sanctioned the same way a pointer
                // position is: a seam conversion (`from_ptr`, `from_raw`,
                // `from_void_ptr`) and the C-ABI gateway are expected to be
                // unsafe; anything else is exporting an obligation.
                if sig.safety().is_unsafe() {
                    let site = counter_site(tcx, tcx.def_span(did));
                    c.unsafe_fns += 1;
                    sites.add("unsafe_fns", site.clone());
                    if seam || in_ffi {
                        c.unsafe_fns_seam += 1;
                        sites.add("unsafe_fns_seam", site);
                    } else if exported {
                        c.unsafe_fns_pub_smell += 1;
                        sites.add("unsafe_fns_pub_smell", site);
                    } else {
                        c.unsafe_fns_priv_smell += 1;
                        sites.add("unsafe_fns_priv_smell", site);
                    }
                }
                // Raw-pointer args/rets: count EVERY position, then name the
                // sanctioned subset. No position goes unreported.
                let sanctioned = seam || in_ffi;
                // Resolution-based self-boundary: a raw ptr to the method's OWN
                // wrapper type (`*mut Self` in `free`/`dispose`/`dup`/…) is the
                // type's raw-form lifecycle seam, not a "use the wrapper" smell
                // (you can't pass `&Self` while destroying/duplicating it). Skip.
                let own_self = enclosing_impl_self(tcx, did);
                {
                    let mut tally = |p: Ty<'_>, is_ret: bool, c: &mut Counts| {
                        let site = counter_site(tcx, tcx.def_span(did));
                        if is_ret {
                            c.raw_ptr_rets += 1;
                            sites.add("raw_ptr_rets", site.clone());
                        } else {
                            c.raw_ptr_args += 1;
                            sites.add("raw_ptr_args", site.clone());
                        }
                        // A raw ptr to the method's OWN wrapper type (`*mut Self`
                        // in `free`/`dup`) is the type's raw-form lifecycle seam —
                        // you cannot pass `&Self` while destroying it. Sanctioned,
                        // and now COUNTED as such instead of dropped silently.
                        let is_own =
                            own_self.is_some_and(|s| p.ty_adt_def().map(|d| d.did()) == Some(s));
                        if sanctioned || is_own {
                            c.raw_ptr_seam += 1;
                            sites.add("raw_ptr_seam", site);
                            return;
                        }
                        // Every unsanctioned position is smell, and listed.
                        if exported {
                            c.raw_ptr_pub_smell += 1;
                            sites.add("raw_ptr_pub_smell", site.clone());
                        } else {
                            c.raw_ptr_priv_smell += 1;
                            sites.add("raw_ptr_priv_smell", site.clone());
                        }
                        // Of those, the most actionable: a raw ptr to the *C type* when
                        // a wrapper exists (`*mut ffi::git_oid` → should be GitOid).
                        if matches!(p.kind(),
                            ty::TyKind::Adt(def, _) if wrapped_c.contains(&def.did()))
                        {
                            c.raw_ptr_wrapped += 1;
                            sites.add("raw_ptr_wrapped", site);
                        }
                    };
                    for inp in sig.inputs() {
                        let mut pointees = Vec::new();
                        raw_pointees(tcx, *inp, &mut pointees);
                        for p in pointees {
                            tally(p, false, &mut c);
                        }
                    }
                    let mut pointees = Vec::new();
                    raw_pointees(tcx, sig.output(), &mut pointees);
                    for p in pointees {
                        tally(p, true, &mut c);
                    }
                }
            }
        }
        // Crate-wide code LoC — the denominator. Built from the COMPILED crate
        // (the union of HIR definition spans), not from the raw file text.
        //
        // Reading the text counted every line physically present, including
        // items `cfg` removed before HIR: an inline `#[cfg(test)] mod tests`
        // put its lines in the denominator while its bodies — never compiled
        // under `cargo build` — could reach no numerator, so the unsafe ratio
        // read low in proportion to test coverage. A definition that did not
        // survive `cfg` has no `DefId`, so unioning def spans excludes it by
        // construction, and generalises to every `#[cfg(..)]`-disabled item
        // (feature gates, platform gates) rather than special-casing `test`.
        //
        // Two details make the union tight:
        //  * `source_callsite()` maps a macro-expanded def back to its
        //    invocation, so generated items are charged to the `define_ctype!`
        //    line that produced them rather than to ffibox's source.
        //  * CONTAINERS (`mod` / `impl` / `trait` / `extern` blocks) contribute
        //    only their opening and closing lines, never their full span: a
        //    container's span still covers the text of items `cfg` stripped out
        //    of it (the crate-root module's span is the whole file), so
        //    unioning it whole would reinstate exactly what this is removing.
        //    Their members are separate definitions and bring their own bodies.
        //  * BODIES are unioned separately, because `def_span` on a fn is its
        //    SIGNATURE span, not the item's. Definitions alone counted headers
        //    and no statements -- 4208 lines where git2's source has 20990,
        //    which read as an 83% unsafe ratio.
        //
        // The line set is per file and deduplicated, so items sharing a line
        // (or several defs from one macro invocation) count it once. The
        // blank / `//`-comment filter is the same one `unsafe_block_code_lines`
        // applies, so numerator and denominator stay apples-to-apples.
        {
            let sm = tcx.sess.source_map();
            // file (keyed by its source-map start offset) -> covered 1-based lines
            let mut covered: HashMap<u32, HashSet<usize>> = HashMap::new();
            for ld in tcx.hir_crate_items(()).definitions() {
                let did = ld.to_def_id();
                let container = matches!(
                    tcx.def_kind(did),
                    DefKind::Mod | DefKind::Impl { .. } | DefKind::Trait | DefKind::ForeignMod
                );
                let sp = tcx.def_span(did).source_callsite();
                let lo = sm.lookup_char_pos(sp.lo());
                let hi = sm.lookup_char_pos(sp.hi());
                // Local crate only (imported files carry `src == None`), and
                // skip the pathological span that straddles two files.
                if lo.file.src.is_none() || lo.file.start_pos != hi.file.start_pos {
                    continue;
                }
                let e = covered.entry(lo.file.start_pos.0).or_default();
                if container {
                    e.insert(lo.line);
                    e.insert(hi.line);
                } else {
                    e.extend(lo.line..=hi.line);
                }
            }
            // Bodies: fn / const / static initializers and closures. Same
            // `cfg` guarantee -- a stripped item owns no body -- and the same
            // dedup, so a body overlapping its own signature line counts once.
            for owner in tcx.hir_body_owners() {
                let sp = tcx.hir_body_owned_by(owner).value.span.source_callsite();
                let lo = sm.lookup_char_pos(sp.lo());
                let hi = sm.lookup_char_pos(sp.hi());
                if lo.file.src.is_none() || lo.file.start_pos != hi.file.start_pos {
                    continue;
                }
                covered
                    .entry(lo.file.start_pos.0)
                    .or_default()
                    .extend(lo.line..=hi.line);
            }
            for sf in sm.files().iter() {
                let (Some(src), Some(set)) = (&sf.src, covered.get(&sf.start_pos.0)) else {
                    continue;
                };
                c.code_lines += src
                    .lines()
                    .enumerate()
                    .filter(|(i, l)| {
                        let t = l.trim();
                        set.contains(&(i + 1)) && !t.is_empty() && !t.starts_with("//")
                    })
                    .count() as u64;
            }
        }
        println!(
            "{{\"crate\":\"{}\",\"unsafe_blocks\":{},\"unsafe_block_stmts\":{},\"unsafe_block_lines\":{},\"unsafe_block_code_lines\":{},\"unsafe_blocks_wrapper_impl\":{},\"unsafe_blocks_ffi_export\":{},\"unsafe_fns\":{},\"unsafe_fns_seam\":{},\"unsafe_fns_pub_smell\":{},\"unsafe_fns_priv_smell\":{},\"unsafe_impls\":{},\"unsafe_traits\":{},\"ffi_calls\":{},\"wrapper_newtypes\":{},\"wrapper_newtypes_declared\":{},\"wrapper_declared_nonconformant\":{},\"wrapper_newtypes_undeclared\":{},\"raw_ptr_args\":{},\"raw_ptr_rets\":{},\"raw_ptr_seam\":{},\"raw_ptr_wrapped\":{},\"raw_ptr_pub_smell\":{},\"raw_ptr_priv_smell\":{},\"ref_to_type_wrapper_sanctioned\":{},\"ref_to_type_wrapper_smell\":{},\"ref_to_type_wrapper_body_smell\":{},\"deref_impl_on_wrapper\":{},\"raw_ptr_fields\":{},\"field_proj_wrapped\":{},\"field_proj_outside_impl\":{},\"field_ref_wrapped\":{},\"void_ptr_seam\":{},\"void_ptr_pub_smell\":{},\"void_ptr_priv_smell\":{},\"raw_ptr_derefs\":{},\"raw_ptr_derefs_outside_impl\":{},\"total_stmts\":{},\"code_lines\":{},\"sites\":{}}}",
            krate, c.unsafe_blocks, c.unsafe_block_stmts, c.unsafe_block_lines, c.unsafe_block_code_lines, c.unsafe_blocks_wrapper_impl, c.unsafe_blocks_ffi_export, c.unsafe_fns, c.unsafe_fns_seam, c.unsafe_fns_pub_smell, c.unsafe_fns_priv_smell, c.unsafe_impls, c.unsafe_traits, c.ffi_calls, c.wrapper_newtypes, c.wrapper_newtypes_declared, c.wrapper_declared_nonconformant, c.wrapper_newtypes_undeclared, c.raw_ptr_args, c.raw_ptr_rets, c.raw_ptr_seam, c.raw_ptr_wrapped, c.raw_ptr_pub_smell, c.raw_ptr_priv_smell, c.ref_to_type_wrapper_sanctioned, c.ref_to_type_wrapper_smell, c.ref_to_type_wrapper_body_smell, c.deref_impl_on_wrapper, c.raw_ptr_fields, c.field_proj_wrapped, c.field_proj_outside_impl, c.field_ref_wrapped, c.void_ptr_seam, c.void_ptr_pub_smell, c.void_ptr_priv_smell, c.raw_ptr_derefs, c.raw_ptr_derefs_outside_impl, c.total_stmts, c.code_lines,
            sites.json()
        );
        Compilation::Continue
    }
}

fn main() {
    let mut args: Vec<String> = std::env::args().collect();
    if !args
        .iter()
        .any(|a| a == "--sysroot" || a.starts_with("--sysroot="))
    {
        // `SYSROOT` env (set to the *nightly* sysroot) wins; else ask rustc.
        let sysroot = std::env::var("SYSROOT").unwrap_or_else(|_| {
            let out = std::process::Command::new("rustc")
                .args(["--print", "sysroot"])
                .output()
                .expect("run rustc --print sysroot");
            String::from_utf8(out.stdout).unwrap().trim().to_string()
        });
        args.push("--sysroot".into());
        args.push(sysroot);
    }
    rustc_driver::compiler_entrypoint(&args, &mut MetricsCallbacks);
}
