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
use rustc_span::hygiene::ExpnKind;
use rustc_span::Span;
use std::collections::{HashMap, HashSet};

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
/// Membership is decided by shape alone (`structural_wrapper`), after macro
/// expansion, so `define_ctype!`-generated and hand-written wrappers are seen
/// alike, whether or not they declare `CCell`.
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
fn contains_ref_to_type_wrapper<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>) -> bool {
    let is_w = |t: Ty<'_>| matches!(t.kind(), ty::TyKind::Adt(d, _) if is_type_wrapper(tcx, d.did()));
    match t.kind() {
        ty::TyKind::Ref(_, inner, m) if !m.is_mut() && has_unsafe_cell(tcx, *inner, 0) => false,
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

/// True when `did` is a method of an impl of a trait another crate defines
/// (`Clone`, `Drop`, ffibox's `CDrop`, ..). That crate fixed its signature, so
/// its raw pointers and `unsafe` are not the measured crate's surface.
fn in_foreign_trait_impl(tcx: TyCtxt<'_>, did: DefId) -> bool {
    let Some(parent) = tcx.opt_parent(did) else {
        return false;
    };
    matches!(tcx.def_kind(parent), DefKind::Impl { of_trait: true })
        && !tcx.impl_trait_ref(parent).skip_binder().def_id.is_local()
}

/// Where a raw-pointer position sits: a field of a type, or a fn signature.
#[derive(Clone, Copy)]
enum PtrSite {
    /// A field, by the effective visibility of its TYPE and, for an exported
    /// type, of the field itself (reachable from outside the crate or not).
    Type { exported: bool, field_exported: bool },
    /// A parameter or return, by the fn's effective visibility and safety.
    Fn { exported: bool, safe: bool },
}

impl PtrSite {
    /// The `raw_ptr_*` and `void_ptr_*` partition counters for this position.
    fn counters(self) -> (&'static str, &'static str) {
        match self {
            PtrSite::Type { exported: true, field_exported: true } => {
                ("raw_ptr_ty_pub_fields_pub", "void_ptr_ty_pub_fields_pub")
            }
            PtrSite::Type { exported: true, field_exported: false } => {
                ("raw_ptr_ty_pub_fields_priv", "void_ptr_ty_pub_fields_priv")
            }
            PtrSite::Type { exported: false, .. } => ("raw_ptr_ty_priv", "void_ptr_ty_priv"),
            PtrSite::Fn { exported: true, safe: true } => ("raw_ptr_fn_pub_safe", "void_ptr_fn_pub_safe"),
            PtrSite::Fn { exported: true, safe: false } => ("raw_ptr_fn_pub_unsafe", "void_ptr_fn_pub_unsafe"),
            PtrSite::Fn { exported: false, safe: true } => ("raw_ptr_fn_priv_safe", "void_ptr_fn_priv_safe"),
            PtrSite::Fn { exported: false, safe: false } => ("raw_ptr_fn_priv_unsafe", "void_ptr_fn_priv_unsafe"),
        }
    }
}

/// Count one raw-pointer position (pointee `p`) into its partition,
/// `raw_ptr_ty_{pub,priv}` or `raw_ptr_fn_{pub,priv}_{safe,unsafe}`;
/// `*c_void` positions likewise into `void_ptr_*`, and a pointee with a wrapper
/// into `raw_ptr_has_ty_wrapper`.
fn count_ptr_position(
    tcx: TyCtxt<'_>,
    p: Ty<'_>,
    at: PtrSite,
    wrapped_c: &HashSet<DefId>,
    site: (String, usize),
    c: &mut Counts,
    sites: &mut Sites,
) {
    let (raw, void) = at.counters();
    *c.slot(raw) += 1;
    sites.add(raw, site.clone());
    if is_c_void(tcx, p) {
        *c.slot(void) += 1;
        sites.add(void, site.clone());
    }
    if matches!(p.kind(), ty::TyKind::Adt(d, _) if wrapped_c.contains(&d.did())) {
        c.raw_ptr_has_ty_wrapper += 1;
        sites.add("raw_ptr_has_ty_wrapper", site);
    }
}

/// The references in `t` (`&T` / `&mut T`, nested ones included) to something
/// that is not C's: `T`, or a slice or array's element, is neither a layout
/// wrapper (`ty_wrapper_borrow_*` counts those) nor C-reachable. `&CStr`,
/// `&str`, `&[u8]`, `&mut Config` all count: memory that stays on the Rust
/// side of the boundary.
fn non_wrapper_borrows<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>) -> u64 {
    let is_c = |u: Ty<'tcx>| {
        let u = match u.kind() {
            ty::TyKind::Slice(e) | ty::TyKind::Array(e, _) => *e,
            _ => u,
        };
        matches!(peel_transparent(tcx, u).kind(), ty::TyKind::Adt(d, _)
            if is_type_wrapper(tcx, d.did()) || is_c_visible(tcx, d.did()))
    };
    match t.kind() {
        ty::TyKind::Ref(_, p, _) => u64::from(!is_c(*p)) + non_wrapper_borrows(tcx, *p),
        ty::TyKind::Adt(d, args) if tcx.item_name(d.did()).as_str() != "PhantomData" => {
            args.types().map(|a| non_wrapper_borrows(tcx, a)).sum()
        }
        ty::TyKind::Tuple(tys) => tys.iter().map(|a| non_wrapper_borrows(tcx, a)).sum(),
        ty::TyKind::Array(e, _) | ty::TyKind::Slice(e) | ty::TyKind::RawPtr(e, _) => non_wrapper_borrows(tcx, *e),
        _ => 0,
    }
}

/// Raw-pointer positions in the fields of a struct or union the crate declares
/// (nested ones included, as for signatures), counted into
/// `raw_ptr_ty_{pub,priv}` by the effective visibility of the TYPE: every
/// raw pointer a public type holds counts, private fields included, since it
/// is that type's representation.
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
    let exported = did.as_local().is_some_and(|l| tcx.effective_visibilities(()).is_exported(l));
    for f in tcx.adt_def(did).all_fields() {
        let ft = tcx.type_of(f.did).instantiate_identity().skip_norm_wip();
        let mut pointees = Vec::new();
        raw_pointees(tcx, ft, &mut pointees);
        let site = counter_site(tcx, tcx.def_span(f.did));
        let field_exported = f.did.as_local().is_some_and(|l| tcx.effective_visibilities(()).is_exported(l));
        for p in pointees {
            count_ptr_position(tcx, p, PtrSite::Type { exported, field_exported }, wrapped_c, site.clone(), c, sites);
        }
    }
}

/// True if `t` is a raw pointer or a `NonNull`.
fn is_raw_or_non_null(tcx: TyCtxt<'_>, t: Ty<'_>) -> bool {
    t.is_raw_ptr()
        || matches!(t.kind(), ty::TyKind::Adt(d, _) if tcx.item_name(d.did()).as_str() == "NonNull")
}

fn is_ref_to_type_wrapper<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>) -> bool {
    if let ty::TyKind::Ref(_, pointee, m) = t.kind() {
        // A shared `&W` over `UnsafeCell` storage asserts neither readonly
        // nor noalias: only `&mut W` is the hazard there.
        if !m.is_mut() && has_unsafe_cell(tcx, *pointee, 0) {
            return false;
        }
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
// ------------------------------------------------------------ C visibility
//
// Which types C can reach memory of. `#[repr(C)]` alone does not say: Rust
// crates use it for their own layouts too. So C reachability is decided by
// provenance, as a closure over the types the build hands to C:
//
//  * seeds: every type behind a pointer (`*const T`, `*mut T`, `&T`,
//    `NonNull<T>`, nested) in the signature of a foreign fn (an `extern`
//    block), of a fn the crate defines with a non-Rust ABI (callbacks, the
//    `#[no_mangle]` gateway), or of a C-ABI fn-pointer type anywhere in the
//    crate (vtables, callback slots); a foreign static's own type; the types
//    a pointer cast or transmute converts to or from `*c_void` (a payload
//    handed to C, or C memory typed by Rust); and every `#[repr(C)]` type of
//    a sys crate, one with a Cargo `links` key (`UM_SYS_CRATES`);
//  * closure: a field a reachable type holds by value, or points to; either
//    side of a pointer cast or transmute whose other side is reachable; and a
//    local `#[repr(C)]` / `#[repr(transparent)]` type that holds a reachable
//    type by value (a wrapper whose bytes are C's).
//
// Passing a type by VALUE is a copy and seeds nothing. Generic wrappers
// (`W<T>` over a C type) and memory C reaches through an erased `void *`
// with no visible cast are not seen; a reachable TYPE does not mean every
// value of it lives in C memory (see docs/audit/unsafe-output.md).

/// The crates whose `#[repr(C)]` types are C's, by crate name: `UM_SYS_CRATES`,
/// comma-separated, set by `scan-unsafe` from Cargo's `links` keys plus
/// `--sys-crates`.
fn sys_crates() -> &'static HashSet<String> {
    static SYS: std::sync::OnceLock<HashSet<String>> = std::sync::OnceLock::new();
    SYS.get_or_init(|| {
        std::env::var("UM_SYS_CRATES")
            .unwrap_or_default()
            .split(',')
            .map(|n| n.trim().replace('-', "_"))
            .filter(|n| !n.is_empty())
            .collect()
    })
}

fn is_sys_c_type(tcx: TyCtxt<'_>, did: DefId) -> bool {
    matches!(tcx.def_kind(did), DefKind::Struct | DefKind::Union | DefKind::Enum)
        && tcx.adt_def(did).repr().c()
        && sys_crates().contains(tcx.crate_name(did.krate).as_str())
}

fn is_std_crate(tcx: TyCtxt<'_>, did: DefId) -> bool {
    matches!(tcx.crate_name(did.krate).as_str(), "core" | "alloc" | "std")
}

/// The ADTs behind a pointer in `t` (`behind` once a pointer was crossed):
/// raw pointers, references, `NonNull`, nested in generics, tuples and arrays,
/// pointers to pointers included, and the parameters and return of a C-ABI
/// fn-pointer type.
fn c_pointee_adts<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>, behind: bool, out: &mut Vec<DefId>) {
    match t.kind() {
        ty::TyKind::RawPtr(p, _) | ty::TyKind::Ref(_, p, _) => c_pointee_adts(tcx, *p, true, out),
        ty::TyKind::Pat(base, _) => c_pointee_adts(tcx, *base, behind, out),
        ty::TyKind::Adt(d, args) => {
            let name = tcx.item_name(d.did());
            if name.as_str() == "PhantomData" {
                return;
            }
            if name.as_str() == "NonNull" {
                for a in args.types() {
                    c_pointee_adts(tcx, a, true, out);
                }
                return;
            }
            if behind && !is_std_crate(tcx, d.did()) {
                out.push(d.did());
            }
            for a in args.types() {
                c_pointee_adts(tcx, a, false, out);
            }
        }
        ty::TyKind::Tuple(tys) => {
            for a in tys.iter() {
                c_pointee_adts(tcx, a, behind, out);
            }
        }
        ty::TyKind::Array(e, _) | ty::TyKind::Slice(e) => c_pointee_adts(tcx, *e, behind, out),
        ty::TyKind::FnPtr(sig_tys, hdr) if hdr.abi() != ExternAbi::Rust => {
            for a in sig_tys.skip_binder().inputs_and_output.iter() {
                c_pointee_adts(tcx, a, false, out);
            }
        }
        _ => {}
    }
}

/// The ADTs C reaches through every C-ABI fn-pointer type nested in `t`.
fn c_fnptr_adts<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>, out: &mut Vec<DefId>) {
    match t.kind() {
        ty::TyKind::FnPtr(_, hdr) if hdr.abi() != ExternAbi::Rust => c_pointee_adts(tcx, t, false, out),
        ty::TyKind::RawPtr(p, _) | ty::TyKind::Ref(_, p, _) | ty::TyKind::Pat(p, _) => c_fnptr_adts(tcx, *p, out),
        ty::TyKind::Array(e, _) | ty::TyKind::Slice(e) => c_fnptr_adts(tcx, *e, out),
        ty::TyKind::Tuple(tys) => {
            for a in tys.iter() {
                c_fnptr_adts(tcx, a, out);
            }
        }
        ty::TyKind::Adt(_, args) => {
            for a in args.types() {
                c_fnptr_adts(tcx, a, out);
            }
        }
        _ => {}
    }
}

/// The pointee of a raw pointer or reference, peeled to its ADT.
fn ptr_pointee_adt<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>) -> Option<Ty<'tcx>> {
    match t.kind() {
        ty::TyKind::RawPtr(p, _) | ty::TyKind::Ref(_, p, _) => Some(peel_transparent(tcx, *p)),
        _ => None,
    }
}

/// Pointer casts and transmutes in the crate's bodies, as the C-reachability
/// seeds and pairs they imply.
struct CastCollector<'a, 'tcx> {
    tcx: TyCtxt<'tcx>,
    typeck: &'tcx TypeckResults<'tcx>,
    seeds: &'a mut Vec<DefId>,
    pairs: &'a mut Vec<(DefId, DefId)>,
}

impl<'a, 'tcx> CastCollector<'a, 'tcx> {
    fn record(&mut self, from: Ty<'tcx>, to: Ty<'tcx>) {
        let (Some(a), Some(b)) = (ptr_pointee_adt(self.tcx, from), ptr_pointee_adt(self.tcx, to)) else {
            return;
        };
        let adt = |t: Ty<'tcx>| match t.kind() {
            ty::TyKind::Adt(d, _) if !is_std_crate(self.tcx, d.did()) => Some(d.did()),
            _ => None,
        };
        match (adt(a), adt(b)) {
            (Some(x), Some(y)) if x != y => self.pairs.push((x, y)),
            // `*mut T as *mut c_void` hands T to C; `*mut c_void as *mut T`
            // types C's memory as T.
            (Some(x), None) if is_c_void(self.tcx, b) => self.seeds.push(x),
            (None, Some(y)) if is_c_void(self.tcx, a) => self.seeds.push(y),
            _ => {}
        }
    }
}

impl<'a, 'tcx> Visitor<'tcx> for CastCollector<'a, 'tcx> {
    fn visit_expr(&mut self, e: &'tcx hir::Expr<'tcx>) {
        match e.kind {
            hir::ExprKind::Cast(inner, _) => {
                self.record(self.typeck.expr_ty(inner), self.typeck.expr_ty(e));
            }
            // `p.cast::<U>()`
            hir::ExprKind::MethodCall(seg, recv, _, _) if seg.ident.as_str() == "cast" => {
                self.record(self.typeck.expr_ty(recv), self.typeck.expr_ty(e));
            }
            // `transmute::<*mut T, *mut U>(p)`
            hir::ExprKind::Call(f, [arg]) => {
                if let hir::ExprKind::Path(ref qp) = f.kind {
                    if let hir::def::Res::Def(_, did) = self.typeck.qpath_res(qp, f.hir_id) {
                        if self.tcx.item_name(did).as_str() == "transmute" && is_std_crate(self.tcx, did) {
                            self.record(self.typeck.expr_ty(arg), self.typeck.expr_ty(e));
                        }
                    }
                }
            }
            _ => {}
        }
        intravisit::walk_expr(self, e);
    }
}

fn compute_c_visible(tcx: TyCtxt<'_>) -> HashSet<DefId> {
    let mut seeds: Vec<DefId> = Vec::new();
    let mut pairs: Vec<(DefId, DefId)> = Vec::new();
    let mut local_layouts: Vec<DefId> = Vec::new();
    for ld in tcx.hir_crate_items(()).definitions() {
        let did = ld.to_def_id();
        match tcx.def_kind(did) {
            DefKind::Fn | DefKind::AssocFn => {
                let sig = tcx.fn_sig(did).skip_binder().skip_binder();
                let c_side = tcx.is_foreign_item(did) || sig.abi() != ExternAbi::Rust;
                for t in sig.inputs_and_output.iter() {
                    if c_side {
                        c_pointee_adts(tcx, t, false, &mut seeds);
                    }
                    c_fnptr_adts(tcx, t, &mut seeds);
                }
            }
            DefKind::Static { .. } => {
                let t = tcx.type_of(did).instantiate_identity().skip_norm_wip();
                if tcx.is_foreign_item(did) {
                    if let Some(d) = field_adt(tcx, t) {
                        seeds.push(d.did());
                    }
                    c_pointee_adts(tcx, t, false, &mut seeds);
                }
                c_fnptr_adts(tcx, t, &mut seeds);
            }
            DefKind::Struct | DefKind::Union | DefKind::Enum => {
                let def = tcx.adt_def(did);
                for f in def.all_fields() {
                    c_fnptr_adts(tcx, tcx.type_of(f.did).instantiate_identity().skip_norm_wip(), &mut seeds);
                }
                if (def.repr().c() || def.repr().transparent()) && !def.is_enum() {
                    local_layouts.push(did);
                }
            }
            DefKind::TyAlias => {
                c_fnptr_adts(tcx, tcx.type_of(did).instantiate_identity().skip_norm_wip(), &mut seeds);
            }
            _ => {}
        }
    }
    for owner in tcx.hir_body_owners() {
        let typeck = tcx.typeck(owner);
        CastCollector { tcx, typeck, seeds: &mut seeds, pairs: &mut pairs }
            .visit_body(tcx.hir_body_owned_by(owner));
    }
    let mut vis: HashSet<DefId> = seeds.into_iter().collect();
    let reach = |vis: &HashSet<DefId>, d: DefId| vis.contains(&d) || is_sys_c_type(tcx, d);
    let mut expanded: HashSet<DefId> = HashSet::new();
    loop {
        let before = vis.len();
        // Fields of reachable types: by value, and behind pointers.
        let todo: Vec<DefId> = vis.iter().copied().filter(|d| !expanded.contains(d)).collect();
        for d in todo {
            expanded.insert(d);
            if is_std_crate(tcx, d) || !matches!(tcx.def_kind(d), DefKind::Struct | DefKind::Union | DefKind::Enum) {
                continue;
            }
            for f in tcx.adt_def(d).all_fields() {
                let ft = tcx.type_of(f.did).instantiate_identity().skip_norm_wip();
                if is_phantom(tcx, ft) || is_zst_marker(tcx, ft) {
                    continue;
                }
                if let Some(a) = field_adt(tcx, ft) {
                    if !is_std_crate(tcx, a.did()) {
                        vis.insert(a.did());
                    }
                }
                let mut ps = Vec::new();
                c_pointee_adts(tcx, ft, false, &mut ps);
                vis.extend(ps);
            }
        }
        for &(a, b) in &pairs {
            if reach(&vis, a) {
                vis.insert(b);
            }
            if reach(&vis, b) {
                vis.insert(a);
            }
        }
        // A local layout type holding a reachable type by value.
        for &d in &local_layouts {
            if vis.contains(&d) {
                continue;
            }
            let holds = tcx.adt_def(d).all_fields().any(|f| {
                let ft = tcx.type_of(f.did).instantiate_identity().skip_norm_wip();
                !is_phantom(tcx, ft)
                    && !is_zst_marker(tcx, ft)
                    && field_adt(tcx, ft).is_some_and(|a| reach(&vis, a.did()))
            });
            if holds {
                vis.insert(d);
            }
        }
        if vis.len() == before {
            break;
        }
    }
    vis
}

thread_local! {
    static C_VISIBLE: std::cell::RefCell<Option<HashSet<DefId>>> =
        const { std::cell::RefCell::new(None) };
}

/// True when C can reach memory of type `did` (see the section comment).
fn is_c_visible(tcx: TyCtxt<'_>, did: DefId) -> bool {
    is_sys_c_type(tcx, did)
        || C_VISIBLE.with(|c| {
            let mut b = c.borrow_mut();
            if b.is_none() {
                *b = Some(compute_c_visible(tcx));
            }
            b.as_ref().unwrap().contains(&did)
        })
}

/// True when `t` holds an `UnsafeCell` (directly, or in a field, transitively):
/// a shared `&T` then asserts neither `readonly` nor `noalias` over it.
fn has_unsafe_cell<'tcx>(tcx: TyCtxt<'tcx>, t: Ty<'tcx>, depth: u32) -> bool {
    if depth > 8 {
        return false;
    }
    match t.kind() {
        ty::TyKind::Adt(d, args) => {
            if tcx.lang_items().unsafe_cell_type() == Some(d.did()) {
                return true;
            }
            d.all_fields().any(|f| has_unsafe_cell(tcx, tcx.type_of(f.did).instantiate(tcx, args).skip_norm_wip(), depth + 1))
        }
        ty::TyKind::Array(e, _) => has_unsafe_cell(tcx, *e, depth + 1),
        ty::TyKind::Tuple(tys) => tys.iter().any(|a| has_unsafe_cell(tcx, a, depth + 1)),
        _ => false,
    }
}

/// A `#[repr(transparent)]` newtype over a Rust reference to a C-reachable
/// type: a handle shape that nonetheless IS a reference into C memory.
fn is_ref_handle_to_c(tcx: TyCtxt<'_>, did: DefId) -> bool {
    let def = tcx.adt_def(did);
    if !def.is_struct() || !def.repr().transparent() {
        return false;
    }
    let inner = peel_transparent(tcx, tcx.type_of(did).instantiate_identity().skip_norm_wip());
    matches!(inner.kind(), ty::TyKind::Ref(_, p, _)
        if matches!(peel_transparent(tcx, *p).kind(), ty::TyKind::Adt(d, _) if is_c_visible(tcx, d.did())))
}

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
/// `--ffibox`'s `ffibox_ccell_not_layout` / `ffibox_layout_not_ccell`, where the
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
/// without the layout it claims: reported by `--ffibox` as
/// `ffibox_ccell_not_layout`, never silently admitted.
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

/// The C types whose BYTES `did` stores inline, transitively: every field held
/// by value whose type C can reach (`is_c_visible`). A local `#[repr(C)]` field
/// C does not reach is RECURSED into rather than accepted, so a wrapper that
/// reaches C through its own intermediate struct still resolves, while a
/// sys crate's own aggregate (`git_index_entry { ctime: git_index_time, .. }`)
/// is a C type, not a wrapper of one, since it is not local. Depth- and
/// cycle-guarded.
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
        if is_c_visible(tcx, d.did()) {
            if !out.contains(&d.did()) {
                out.push(d.did());
            }
        } else if d.did().is_local() && d.repr().c() && seen.insert(d.did()) {
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
///   * LAYOUT -- every C-reachable type `embedded_c` finds held by value, or,
///     for a local type C reaches itself, none. `W` itself must be
///     `#[repr(C)]` or `#[repr(transparent)]`; both give it C's bytes.
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
    // LAYOUT: C's bytes inline -- a type holding a C-reachable type by value,
    // or a local C type C reaches itself (a hand-written mirror, a payload).
    // A sys crate's own aggregates (`git_diff_delta { old_file: git_diff_file,
    // .. }`) are C types, never wrappers of one.
    if sys_crates().contains(tcx.crate_name(did.krate).as_str()) {
        return None;
    }
    if def.repr().c() || def.repr().transparent() {
        let mut cs = Vec::new();
        let mut seen = HashSet::from([did]);
        embedded_c(tcx, did, 0, &mut seen, &mut cs);
        if !cs.is_empty() {
            return Some((true, cs));
        }
        if did.is_local() && is_c_visible(tcx, did) {
            return Some((true, Vec::new()));
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
/// Both are the port stage's C-ABI gateway: the unsafe blocks inside belong to
/// the boundary rather than to the port body, so `unsafe_blocks_ffi_export`
/// counts them apart. Its raw pointers are counted like any other position.
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
    code_lines: u64, // crate-wide physical LoC: non-blank, non-`//`-comment source lines
    total_stmts: u64,
    // Safe fns and methods with a body the crate defines, by effective
    // visibility, on the same terms as unsafe_fns_*: fns_pub = safe_fns_pub +
    // unsafe_fns_pub, likewise _priv. Methods implementing another crate's
    // trait are left out.
    safe_fns_pub: u64,
    safe_fns_priv: u64,
    unsafe_blocks: u64,
    unsafe_block_stmts: u64,
    unsafe_block_lines: u64, // raw brace-to-brace span (incl. blanks/comments)
    unsafe_block_code_lines: u64, // non-blank, non-`//`-comment lines only
    unsafe_blocks_wrapper_impl: u64, // unsafe blocks inside `impl <wrapper T>`
    // unsafe blocks at the C-ABI boundary (`in_ffi_export`: `#[no_mangle]` /
    // `#[export_name]` / `extern "C"`)
    unsafe_blocks_ffi_export: u64,
    // `unsafe fn` DECLARATIONS the crate defines, by rustc's effective
    // visibility (callable from outside the crate): unsafe_fns = unsafe_fns_pub
    // + unsafe_fns_priv. `_pub` is the public unsafe surface, an obligation
    // the crate exports to every caller. Methods implementing another crate's
    // trait are left out: that crate fixed their signature.
    unsafe_fns: u64,
    unsafe_fns_pub: u64,
    unsafe_fns_priv: u64,
    unsafe_impls: u64,
    unsafe_traits: u64,
    // Layout newtypes, found by shape (`structural_wrapper`): a
    // `#[repr(C)]` / `#[repr(transparent)]` struct storing a C-reachable type's
    // bytes inline (see "C visibility"). How these relate to ffibox's `CCell` is the `--ffibox` record's
    // (`ffibox_layout_not_ccell` / `ffibox_ccell_not_layout`).
    ty_wrapper: u64,
    // `#[repr(transparent)]` newtypes over a Rust reference to a C-reachable
    // type: handle-shaped, yet a reference into C memory. Target 0.
    ty_wrapper_borrow_handles: u64,
    // `&W` / `&mut W` (incl. the receiver), W a layout newtype, partitioned:
    // sanctioned (REF_ACCESSORS / STD_VALUE_TRAITS impls) + smell (the rest)
    ty_wrapper_borrow_sanctioned: u64,
    ty_wrapper_borrow_smell: u64,
    // in function BODIES: a `&W` / `&mut W` (or `&[W]`, `Option<&W>`, ..) formed
    // from a raw pointer -- `&*p`, `&(*p).f`, an autoref through `*p`, or a
    // non-local call such as `p.as_ref()` / `NonNull::as_ref` /
    // `slice::from_raw_parts`. Never sanctioned: target 0.
    ty_wrapper_borrow_body_smell: u64,
    // `&T` / `&mut T` in fn signatures (the receiver and nested references
    // included), by the fn's visibility and safety as for raw_ptr_fn_*, where
    // `T` -- or a slice's element --
    // is neither a layout wrapper nor C-reachable: `&CStr`, `&str`, `&[u8]`,
    // `&mut Config`. The counterpart of ty_wrapper_borrow_*: borrows that stay
    // on the Rust side of the boundary. A reference to a C type itself counts
    // in neither.
    ty_non_wrapper_borrow_pub_safe: u64,
    ty_non_wrapper_borrow_pub_unsafe: u64,
    ty_non_wrapper_borrow_priv_safe: u64,
    ty_non_wrapper_borrow_priv_unsafe: u64,
    // Raw-pointer positions in the items the crate defines, nested ones
    // included, each in exactly one counter by where it sits:
    //   raw_ptr_ty_pub_fields_{pub,priv}, raw_ptr_ty_priv  (fields of types)
    //   raw_ptr_fn_{pub,priv}_{safe,unsafe}               (fn signatures)
    // A field counts by its TYPE's effective visibility and, in a public type,
    // by whether the field itself is reachable from outside the crate. A
    // signature counts by the fn's effective visibility and its safety: `_safe`
    // is reachable from safe code, `_unsafe` only by an `unsafe fn` caller.
    // raw_ptr_ty_pub_fields_pub + raw_ptr_fn_pub_safe are the raw pointers on
    // the safe public interface.
    // Methods implementing another crate's trait are left out: that crate
    // fixed their signature.
    raw_ptr_ty_pub_fields_pub: u64,
    raw_ptr_ty_pub_fields_priv: u64,
    raw_ptr_ty_priv: u64,
    raw_ptr_fn_pub_safe: u64,
    raw_ptr_fn_pub_unsafe: u64,
    raw_ptr_fn_priv_safe: u64,
    raw_ptr_fn_priv_unsafe: u64,
    // of those positions, the ones whose pointee is a C type with a wrapper
    // (`*mut ffi::git_oid` where `GitOid` exists)
    raw_ptr_has_ty_wrapper: u64,
    raw_ptr_derefs: u64,
    raw_ptr_derefs_outside_impl: u64, // ...of those, the subset NOT in any impl/trait body
    // the `*c_void` positions among them, partitioned the same way:
    // void_ptr_ty_pub_fields_{pub,priv}, void_ptr_ty_priv,
    // void_ptr_fn_{pub,priv}_{safe,unsafe}
    void_ptr_ty_pub_fields_pub: u64,
    void_ptr_ty_pub_fields_priv: u64,
    void_ptr_ty_priv: u64,
    void_ptr_fn_pub_safe: u64,
    void_ptr_fn_pub_unsafe: u64,
    void_ptr_fn_priv_safe: u64,
    void_ptr_fn_priv_unsafe: u64,
    // `(*p).field` where `p: *C` and `C` has a wrapper (bypasses the
    // accessor): total, and the subset outside any impl/trait (the smell).
    ty_field_proj_wrapped: u64,
    ty_field_proj_outside_impl: u64,
    // `&(*p).field` / `&mut (*p).field` where `p: *C` and `C` has a wrapper --
    // a reference one level down into memory C may write. Should be 0.
    ty_field_borrow_wrapped: u64,
    // `impl Deref` / `impl DerefMut` (core) whose Self is a wrapper, layout or
    // handle. Never sanctioned: target 0.
    deref_impl_on_wrapper: u64,
    // Calls to a foreign item -- one declared in an `extern` block
    // (`is_foreign_item`), which is the FFI boundary itself and is
    // crate-agnostic: a bindgen `*-sys` binding, `libc`, or a local
    // `extern "C"` block all resolve to it. Calling one is an unsafe op, so
    // this is the crate-wide unsafe-FFI-call surface. Resolution-based on the
    // callee, so alias- and re-export-proof.
    ffi_calls: u64,
}


impl Counts {
    /// The partition counter `name`, for the position helpers.
    fn slot(&mut self, name: &str) -> &mut u64 {
        match name {
            "raw_ptr_ty_pub_fields_pub" => &mut self.raw_ptr_ty_pub_fields_pub,
            "raw_ptr_ty_pub_fields_priv" => &mut self.raw_ptr_ty_pub_fields_priv,
            "raw_ptr_ty_priv" => &mut self.raw_ptr_ty_priv,
            "raw_ptr_fn_pub_safe" => &mut self.raw_ptr_fn_pub_safe,
            "raw_ptr_fn_pub_unsafe" => &mut self.raw_ptr_fn_pub_unsafe,
            "raw_ptr_fn_priv_safe" => &mut self.raw_ptr_fn_priv_safe,
            "raw_ptr_fn_priv_unsafe" => &mut self.raw_ptr_fn_priv_unsafe,
            "void_ptr_ty_pub_fields_pub" => &mut self.void_ptr_ty_pub_fields_pub,
            "void_ptr_ty_pub_fields_priv" => &mut self.void_ptr_ty_pub_fields_priv,
            "void_ptr_ty_priv" => &mut self.void_ptr_ty_priv,
            "void_ptr_fn_pub_safe" => &mut self.void_ptr_fn_pub_safe,
            "void_ptr_fn_pub_unsafe" => &mut self.void_ptr_fn_pub_unsafe,
            "void_ptr_fn_priv_safe" => &mut self.void_ptr_fn_priv_safe,
            "void_ptr_fn_priv_unsafe" => &mut self.void_ptr_fn_priv_unsafe,
            _ => unreachable!("not a position partition: {name}"),
        }
    }
}

/// Source sites `(file, 1-based line)` per counter, keyed by the counter's
/// output name: every increment of a location-counting counter records where it
/// happened. Line and statement totals have none. Aggregated by `Sites::json`.
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
        self.c.ty_wrapper_borrow_body_smell += 1;
        self.sites
            .add("ty_wrapper_borrow_body_smell", counter_site(self.tcx, e.span));
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
                            self.c.ty_field_proj_wrapped += 1;
                            self.sites.add("ty_field_proj_wrapped", counter_site(self.tcx, e.span));
                            if !self.in_impl {
                                self.c.ty_field_proj_outside_impl += 1;
                                self.sites.add("ty_field_proj_outside_impl", counter_site(self.tcx, e.span));
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
                                self.c.ty_field_borrow_wrapped += 1;
                                self.sites.add("ty_field_borrow_wrapped", counter_site(self.tcx, e.span));
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

// --------------------------------------------------------------- ffibox mode

/// `UM_FFIBOX` (`scan-unsafe --ffibox`) counters, each broken down by ffibox
/// type, handle kind or trait. Every one counts source locations, so all take
/// `--sites`. `_pub` / `_priv` is rustc's effective visibility, as elsewhere:
/// of the fn for a signature position, of the implementing type for an impl.
///
///  - `fn_sig_ffibox_owner_*`: an ffibox owner (`CBox`, `CArc`, `CVec`,
///    `CStrBox`, `CVal`) in a parameter or return type, nested ones included,
///    keyed by type name, `_pub` / `_priv` by the fn's visibility.
///  - `fn_sig_ffibox_handle_*`: likewise for ffibox-based borrowed handles: the
///    crate's own, the types its `CCell` / `CGuarded` impls name as `Ref`,
///    `Mut` and `Locked` (keyed by that kind); ffibox's borrowed views
///    (`CSlice`, `CSliceMut`, `CBorrowedPtr`, `CGuardedRef`, `CGuard`, keyed by
///    type); and a hand-built handle over one of those, a
///    `#[repr(transparent)]` newtype over exactly one (keyed by its path). A
///    method's receiver counts here when it is such a handle: that is where a
///    C function's borrowed `T *` lands.
///  - `fn_sig_non_ffibox_owner_*`: likewise for the crate's own owners, the types
///    with an `impl Drop` no ffibox macro emitted (`drop_impl`), keyed by type:
///    ownership the API hands out outside ffibox's `CBox` / `CArc` / `CVec`.
///  - `ty_pub_fields_pub_<kind>`, `ty_pub_fields_priv_<kind>`, `ty_priv_<kind>`:
///    the same three kinds (`ffibox_owner`, `ffibox_handle`, `non_ffibox_owner`)
///    in the fields of the structs, unions and enums the crate defines, split
///    as for `raw_ptr_ty_*`: by the type's effective visibility and, in a
///    public type, by the field's own. What the crate's types hold, where
///    `fn_sig_*` is what its fns take and return. Borrows of non-wrapper
///    memory are a main counter (`ty_non_wrapper_borrow_*`), independent of
///    ffibox.
///  - `ffibox_impl_macro` / `ffibox_impl_manual`: distinct crate-defined types
///    implementing each ffibox trait, keyed by trait, split by whether an
///    ffibox macro (`define_ctype!`, `impl_cdrop!`, ..) emitted the impl.
///  - `ffibox_define_ctype_macro` / `ffibox_define_ctype_manual`: the crate's
///    layout types (its `CCell` implementors), keyed by type, split by whether
///    `define_ctype!` emitted the `CCell` impl or the author wrote it.
///  - `ffibox_ccell_not_layout` / `ffibox_layout_not_ccell`: the crate's types,
///    keyed by type, that implement `CCell` without being layout newtypes by
///    shape (`structural_wrapper`) -- a wrapper without the layout it claims --
///    and the layout newtypes that do not implement `CCell` -- wrappers written
///    outside ffibox.
///  - `drop_impl`: crate-defined types with an `impl Drop` no ffibox macro
///    emitted, keyed by type: owners written instead of ffibox's `CBox` /
///    `CArc` / `CVec`.
///  - `clone_impl`: crate-defined types with a hand-written `impl Clone`
///    (neither derived nor emitted by an ffibox macro), keyed by type: copies
///    written instead of ffibox's clone policies.
const FFIBOX_COUNTERS: &[&str] = &[
    "fn_sig_ffibox_owner_pub",
    "fn_sig_ffibox_owner_priv",
    "fn_sig_ffibox_handle_pub",
    "fn_sig_ffibox_handle_priv",
    "fn_sig_non_ffibox_owner_pub",
    "fn_sig_non_ffibox_owner_priv",
    "ty_pub_fields_pub_ffibox_owner",
    "ty_pub_fields_priv_ffibox_owner",
    "ty_priv_ffibox_owner",
    "ty_pub_fields_pub_ffibox_handle",
    "ty_pub_fields_priv_ffibox_handle",
    "ty_priv_ffibox_handle",
    "ty_pub_fields_pub_non_ffibox_owner",
    "ty_pub_fields_priv_non_ffibox_owner",
    "ty_priv_non_ffibox_owner",
    "ffibox_impl_macro",
    "ffibox_impl_manual",
    "ffibox_define_ctype_macro",
    "ffibox_define_ctype_manual",
    "ffibox_ccell_not_layout",
    "ffibox_layout_not_ccell",
    "drop_impl",
    "clone_impl",
];

/// Compiler-emitted marker impls a `#[derive]` adds beside the trait asked
/// for. They assert nothing the author wrote.
const INTERNAL_MARKER_TRAITS: &[&str] = &["TrivialClone", "StructuralPartialEq"];

fn is_ffibox_crate(tcx: TyCtxt<'_>, did: DefId) -> bool {
    tcx.crate_name(did.krate).as_str() == "ffibox"
}

/// True when `span` is output of an ffibox macro (`define_ctype!`,
/// `impl_cguarded!`, ..), at any depth of expansion. Resolved through the
/// macro's definition, so a renamed import still counts.
fn from_ffibox_macro(tcx: TyCtxt<'_>, span: Span) -> bool {
    let mut ctxt = span.ctxt();
    while !ctxt.is_root() {
        let data = ctxt.outer_expn_data();
        if data.macro_def_id.is_some_and(|m| is_ffibox_crate(tcx, m)) {
            return true;
        }
        ctxt = data.call_site.ctxt();
    }
    false
}

/// The crate's borrowed handles, by kind: the types its `impl CCell` and
/// `impl CGuarded` blocks bind to `Ref`, `Mut` and `Locked`. Read off the
/// impls rather than the names, so `HolderRef<'a, 'x>` is found like `FooRef`.
fn ffibox_handles(tcx: TyCtxt<'_>) -> HashMap<DefId, &'static str> {
    let mut out = HashMap::new();
    for ld in tcx.hir_crate_items(()).definitions() {
        let did = ld.to_def_id();
        if !matches!(tcx.def_kind(did), DefKind::Impl { of_trait: true }) {
            continue;
        }
        let tr = tcx.impl_trait_ref(did).skip_binder().def_id;
        if !is_ffibox_crate(tcx, tr) || !matches!(tcx.item_name(tr).as_str(), "CCell" | "CGuarded") {
            continue;
        }
        for &item in tcx.associated_item_def_ids(did) {
            if tcx.def_kind(item) != DefKind::AssocTy {
                continue;
            }
            let kind = match tcx.item_name(item).as_str() {
                "Ref" => "Ref",
                "Mut" => "Mut",
                "Locked" => "Locked",
                _ => continue,
            };
            let t = tcx.type_of(item).instantiate_identity().skip_norm_wip();
            if let ty::TyKind::Adt(d, _) = t.kind() {
                out.insert(d.did(), kind);
            }
        }
    }
    out
}

/// What a signature position names: an ffibox owner, an ffibox-based
/// borrowed handle (the crate's `CCell` / `CGuarded` handles and ffibox's
/// borrowed views), one of the crate's own owners, another of its borrowed
/// types, or a reference to a standard borrowed view.
#[derive(Clone, Copy, PartialEq)]
enum SigKind {
    FfiboxOwner,
    FfiboxHandle,
    Owner,
}

/// ffibox's owners; its other public types (`CSlice`, `CSliceMut`,
/// `CBorrowedPtr`, `CGuardedRef`, `CGuard`) borrow.
const FFIBOX_OWNERS: &[&str] = &["CBox", "CArc", "CVec", "CStrBox", "CVal"];

/// True when `did` is a `#[repr(transparent)]` newtype over exactly one of
/// ffibox's borrowed types (`CBorrowedPtr`, `CSlice`, `CSliceMut`,
/// `CGuardedRef`, `CGuard`) or of the crate's own `CCell` / `CGuarded`
/// handles: a handle built on ffibox by hand, not one its `CCell` impls name.
/// A record holding such a handle beside other fields is not a handle.
fn holds_ffibox_borrow(tcx: TyCtxt<'_>, did: DefId, handles: &HashMap<DefId, &'static str>) -> bool {
    let def = tcx.adt_def(did);
    if !def.is_struct() || !def.repr().transparent() {
        return false;
    }
    let mut inner = def.all_fields().map(|f| tcx.type_of(f.did).instantiate_identity().skip_norm_wip())
        .filter(|t| !is_phantom(tcx, *t) && !is_zst_marker(tcx, *t));
    matches!((inner.next().map(|t| *t.kind()), inner.next()), (Some(ty::TyKind::Adt(d, _)), None)
        if (is_ffibox_crate(tcx, d.did()) && !FFIBOX_OWNERS.contains(&tcx.item_name(d.did()).as_str()))
            || handles.contains_key(&d.did()))
}

/// Every ffibox type (keyed by its name), crate handle (by kind) and crate
/// owner (by path) in `t`, nested in references, raw pointers, generic
/// arguments, tuples, arrays and slices included. Aliases are already resolved
/// in `t`.
fn ffibox_positions<'tcx>(
    tcx: TyCtxt<'tcx>,
    t: Ty<'tcx>,
    handles: &HashMap<DefId, &'static str>,
    owners: &HashSet<DefId>,
    out: &mut Vec<(SigKind, String)>,
) {
    match t.kind() {
        ty::TyKind::Adt(d, args) => {
            let did = d.did();
            if is_ffibox_crate(tcx, did) {
                let name = tcx.item_name(did);
                let kind = if FFIBOX_OWNERS.contains(&name.as_str()) { SigKind::FfiboxOwner } else { SigKind::FfiboxHandle };
                out.push((kind, name.to_string()));
            } else if let Some(kind) = handles.get(&did) {
                out.push((SigKind::FfiboxHandle, kind.to_string()));
            } else if did.is_local() && holds_ffibox_borrow(tcx, did, handles) {
                // A handle the crate built on ffibox's own borrowed types.
                out.push((SigKind::FfiboxHandle, tcx.def_path_str(did)));
            } else if owners.contains(&did) {
                out.push((SigKind::Owner, tcx.def_path_str(did)));
            }
            for a in args.types() {
                ffibox_positions(tcx, a, handles, owners, out);
            }
        }
        ty::TyKind::Ref(_, p, _) => ffibox_positions(tcx, *p, handles, owners, out),
        ty::TyKind::RawPtr(p, _) => ffibox_positions(tcx, *p, handles, owners, out),
        ty::TyKind::Slice(e) | ty::TyKind::Array(e, _) => ffibox_positions(tcx, *e, handles, owners, out),
        ty::TyKind::Tuple(tys) => {
            for e in tys.iter() {
                ffibox_positions(tcx, e, handles, owners, out);
            }
        }
        _ => {}
    }
}

/// The crate's own owners: local types with an `impl Drop` that no ffibox
/// macro emitted (the `drop_impl` set).
fn own_owners(tcx: TyCtxt<'_>) -> HashSet<DefId> {
    let mut out = HashSet::new();
    for ld in tcx.hir_crate_items(()).definitions() {
        let did = ld.to_def_id();
        if !matches!(tcx.def_kind(did), DefKind::Impl { of_trait: true }) {
            continue;
        }
        let tr = tcx.impl_trait_ref(did).skip_binder().def_id;
        if tcx.crate_name(tr.krate).as_str() != "core"
            || tcx.item_name(tr).as_str() != "Drop"
            || from_ffibox_macro(tcx, tcx.def_span(did))
        {
            continue;
        }
        if let ty::TyKind::Adt(d, _) = tcx.type_of(did).instantiate_identity().skip_norm_wip().kind() {
            if d.did().is_local() {
                out.insert(d.did());
            }
        }
    }
    out
}

type FfiboxTally = std::collections::BTreeMap<&'static str, std::collections::BTreeMap<String, u64>>;

fn ffibox_bump(m: &mut FfiboxTally, sites: &mut Sites, counter: &'static str, key: String, site: (String, usize)) {
    *m.entry(counter).or_default().entry(key).or_default() += 1;
    sites.add(counter, site);
}

/// `UM_FFIBOX`: the crate's ffibox surface, as one JSON line beside the
/// metrics line: `{"crate":..,"ffibox":{"<counter>":{"<key>":N,..},..},"sites":{..}}`.
///
/// Signatures are those of free fns, inherent methods and the crate's own
/// trait declarations. A trait impl's methods are left out: the trait fixes
/// their signatures, and the impl itself is what `*_impl_*` counts. A method's
/// `self` receiver counts only when it is a borrowed handle (an ffibox one or
/// one of the crate's own borrowed types); on an owner or a plain value it
/// borrows a Rust value and is skipped.
fn ffibox_json(tcx: TyCtxt<'_>, krate: rustc_span::Symbol) -> String {
    let handles = ffibox_handles(tcx);
    let owners = own_owners(tcx);
    let mut m: FfiboxTally = FFIBOX_COUNTERS.iter().map(|k| (*k, Default::default())).collect();
    let mut sites = Sites::default();
    let exported = |did: DefId| did.as_local().is_some_and(|l| tcx.effective_visibilities(()).is_exported(l));
    // (trait, implementing type): a type implementing `From<A>` and `From<B>`
    // implements `From` once.
    let mut impls: HashSet<(DefId, DefId)> = HashSet::new();
    for ld in tcx.hir_crate_items(()).definitions() {
        let did = ld.to_def_id();
        match tcx.def_kind(did) {
            DefKind::Fn | DefKind::AssocFn => {
                let in_trait_impl = tcx
                    .opt_parent(did)
                    .is_some_and(|p| matches!(tcx.def_kind(p), DefKind::Impl { of_trait: true }));
                let span = tcx.def_span(did);
                if in_trait_impl || in_generated_file(tcx, span) {
                    continue;
                }
                let public = exported(did);
                let sig = tcx.fn_sig(did).skip_binder().skip_binder();
                let receiver = tcx.def_kind(did) == DefKind::AssocFn && tcx.associated_item(did).is_method();
                let mut found: Vec<(SigKind, String)> = Vec::new();
                // A receiver counts only as a borrowed handle: that is where a C
                // function's borrowed `T *` lands. `&self` on an owner or a plain
                // value borrows a Rust value, not a C object.
                if receiver {
                    let mut recv = Vec::new();
                    ffibox_positions(tcx, sig.inputs()[0], &handles, &owners, &mut recv);
                    found.extend(recv.into_iter().filter(|(k, _)| matches!(k, SigKind::FfiboxHandle)));
                }
                for t in sig
                    .inputs()
                    .iter()
                    .copied()
                    .skip(receiver as usize)
                    .chain(std::iter::once(sig.output()))
                {
                    ffibox_positions(tcx, t, &handles, &owners, &mut found);
                }
                let site = counter_site(tcx, span);
                for (kind, key) in found {
                    let counter = match (kind, public) {
                        (SigKind::FfiboxOwner, true) => "fn_sig_ffibox_owner_pub",
                        (SigKind::FfiboxOwner, false) => "fn_sig_ffibox_owner_priv",
                        (SigKind::FfiboxHandle, true) => "fn_sig_ffibox_handle_pub",
                        (SigKind::FfiboxHandle, false) => "fn_sig_ffibox_handle_priv",
                        (SigKind::Owner, true) => "fn_sig_non_ffibox_owner_pub",
                        (SigKind::Owner, false) => "fn_sig_non_ffibox_owner_priv",
                    };
                    ffibox_bump(&mut m, &mut sites, counter, key, site.clone());
                }
            }
            DefKind::Struct | DefKind::Union | DefKind::Enum => {
                if in_generated_file(tcx, tcx.def_span(did)) {
                    continue;
                }
                if tcx.def_kind(did) == DefKind::Struct {
                    let layout = matches!(structural_wrapper(tcx, did), Some((true, cs)) if !cs.is_empty());
                    let declared = is_declared_wrapper(tcx, did);
                    let site = counter_site(tcx, tcx.def_span(did));
                    if declared && !layout {
                        ffibox_bump(&mut m, &mut sites, "ffibox_ccell_not_layout", tcx.def_path_str(did), site);
                    } else if layout && !declared {
                        ffibox_bump(&mut m, &mut sites, "ffibox_layout_not_ccell", tcx.def_path_str(did), site);
                    }
                }
                let public = exported(did);
                for f in tcx.adt_def(did).all_fields() {
                    let mut found: Vec<(SigKind, String)> = Vec::new();
                    let ft = tcx.type_of(f.did).instantiate_identity().skip_norm_wip();
                    ffibox_positions(tcx, ft, &handles, &owners, &mut found);
                    let site = counter_site(tcx, tcx.def_span(f.did));
                    let field_public = exported(f.did);
                    for (kind, key) in found {
                        let counter = match (kind, public, field_public) {
                            (SigKind::FfiboxOwner, true, true) => "ty_pub_fields_pub_ffibox_owner",
                            (SigKind::FfiboxOwner, true, false) => "ty_pub_fields_priv_ffibox_owner",
                            (SigKind::FfiboxOwner, false, _) => "ty_priv_ffibox_owner",
                            (SigKind::FfiboxHandle, true, true) => "ty_pub_fields_pub_ffibox_handle",
                            (SigKind::FfiboxHandle, true, false) => "ty_pub_fields_priv_ffibox_handle",
                            (SigKind::FfiboxHandle, false, _) => "ty_priv_ffibox_handle",
                            (SigKind::Owner, true, true) => "ty_pub_fields_pub_non_ffibox_owner",
                            (SigKind::Owner, true, false) => "ty_pub_fields_priv_non_ffibox_owner",
                            (SigKind::Owner, false, _) => "ty_priv_non_ffibox_owner",
                        };
                        ffibox_bump(&mut m, &mut sites, counter, key, site.clone());
                    }
                }
            }
            DefKind::Impl { of_trait: true } => {
                let tr = tcx.impl_trait_ref(did).skip_binder().def_id;
                let name = tcx.item_name(tr);
                if INTERNAL_MARKER_TRAITS.contains(&name.as_str()) || name.as_str().starts_with("__") {
                    continue;
                }
                let self_ty = tcx.type_of(did).instantiate_identity().skip_norm_wip();
                let ty::TyKind::Adt(d, _) = self_ty.kind() else {
                    continue;
                };
                let ty_did = d.did();
                if !ty_did.is_local() || !impls.insert((tr, ty_did)) {
                    continue;
                }
                let site = counter_site(tcx, tcx.def_span(did));
                let by_macro = from_ffibox_macro(tcx, tcx.def_span(did));
                if is_ffibox_crate(tcx, tr) {
                    let c = if by_macro { "ffibox_impl_macro" } else { "ffibox_impl_manual" };
                    ffibox_bump(&mut m, &mut sites, c, name.to_string(), site.clone());
                    // A layout type is a `CCell` implementor; `define_ctype!` emits
                    // its `CCell` impl, so the impl's origin is the type's.
                    if name.as_str() == "CCell" {
                        let c = if by_macro { "ffibox_define_ctype_macro" } else { "ffibox_define_ctype_manual" };
                        ffibox_bump(&mut m, &mut sites, c, tcx.def_path_str(ty_did), site);
                    }
                    continue;
                }
                // A crate type's own `Drop` is an owner written instead of
                // ffibox's; one an ffibox macro emitted is ffibox's design.
                if !by_macro && tcx.crate_name(tr.krate).as_str() == "core" {
                    match name.as_str() {
                        "Drop" => ffibox_bump(&mut m, &mut sites, "drop_impl", tcx.def_path_str(ty_did), site),
                        // A `#[derive(Clone)]` copies field by field and is not a
                        // decision about the C object; a hand-written one is.
                        "Clone" if !tcx.is_automatically_derived(did) => {
                            ffibox_bump(&mut m, &mut sites, "clone_impl", tcx.def_path_str(ty_did), site)
                        }
                        _ => {}
                    }
                }
            }
            _ => {}
        }
    }
    let body = m
        .iter()
        .map(|(k, by)| {
            let inner = by.iter().map(|(n, v)| format!("\"{n}\":{v}")).collect::<Vec<_>>().join(",");
            format!("\"{k}\":{{{inner}}}")
        })
        .collect::<Vec<_>>()
        .join(",");
    format!("{{\"crate\":\"{krate}\",\"ffibox\":{{{body}}},\"sites\":{}}}", sites.json())
}

// ---------------------------------------------------------------- seed mode

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
        // `--ffibox`: a second line from the same compilation, beside the
        // metrics line below. The dispatcher tells them apart by key.
        if std::env::var_os("UM_FFIBOX").is_some() {
            println!("{}", ffibox_json(tcx, krate));
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
                    // LAYOUT newtypes only, and only those wrapping a C type: a
                    // local C type C reaches itself is in the reference check
                    // (`is_type_wrapper`) but is not a wrapper of anything. A
                    // handle is a wrapper too, but it is not the set this audit
                    // polices: `&handle` covers Rust-owned pointer storage and
                    // is ordinary, while `&W` on a layout newtype is the hazard
                    // `ty_wrapper_borrow_*` exists to keep at 0.
                    let is_layout = matches!(structural_wrapper(tcx, did), Some((true, cs)) if !cs.is_empty());
                    if is_layout {
                        c.ty_wrapper += 1;
                        sites.add("ty_wrapper", counter_site(tcx, tcx.def_span(did)));
                    }
                    if is_ref_handle_to_c(tcx, did) {
                        c.ty_wrapper_borrow_handles += 1;
                        sites.add("ty_wrapper_borrow_handles", counter_site(tcx, tcx.def_span(did)));
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
                let foreign = in_foreign_trait_impl(tcx, did);
                let safe = !sig.safety().is_unsafe();
                // `&W` / `&mut W` anywhere in the signature.
                for t in sig
                    .inputs()
                    .iter()
                    .copied()
                    .chain(std::iter::once(sig.output()))
                {
                    if is_ref_to_type_wrapper(tcx, t) {
                        let site = counter_site(tcx, tcx.def_span(did));
                        if ref_to_wrapper_sanctioned(tcx, did) {
                            c.ty_wrapper_borrow_sanctioned += 1;
                            sites.add("ty_wrapper_borrow_sanctioned", site);
                        } else {
                            c.ty_wrapper_borrow_smell += 1;
                            sites.add("ty_wrapper_borrow_smell", site);
                        }
                    }
                }
                if safe && !foreign {
                    let site = counter_site(tcx, tcx.def_span(did));
                    if exported {
                        c.safe_fns_pub += 1;
                        sites.add("safe_fns_pub", site);
                    } else {
                        c.safe_fns_priv += 1;
                        sites.add("safe_fns_priv", site);
                    }
                }
                if !safe && !foreign {
                    let site = counter_site(tcx, tcx.def_span(did));
                    c.unsafe_fns += 1;
                    sites.add("unsafe_fns", site.clone());
                    if exported {
                        c.unsafe_fns_pub += 1;
                        sites.add("unsafe_fns_pub", site);
                    } else {
                        c.unsafe_fns_priv += 1;
                        sites.add("unsafe_fns_priv", site);
                    }
                }
                // Borrows of non-wrapper memory in the signature (the receiver
                // included), by the fn's visibility and safety.
                if !foreign {
                    let n: u64 = sig.inputs().iter().copied().chain(std::iter::once(sig.output()))
                        .map(|t| non_wrapper_borrows(tcx, t)).sum();
                    if n > 0 {
                        let site = counter_site(tcx, tcx.def_span(did));
                        let (slot, k) = match (exported, safe) {
                            (true, true) => (&mut c.ty_non_wrapper_borrow_pub_safe, "ty_non_wrapper_borrow_pub_safe"),
                            (true, false) => (&mut c.ty_non_wrapper_borrow_pub_unsafe, "ty_non_wrapper_borrow_pub_unsafe"),
                            (false, true) => (&mut c.ty_non_wrapper_borrow_priv_safe, "ty_non_wrapper_borrow_priv_safe"),
                            (false, false) => (&mut c.ty_non_wrapper_borrow_priv_unsafe, "ty_non_wrapper_borrow_priv_unsafe"),
                        };
                        *slot += n;
                        for _ in 0..n {
                            sites.add(k, site.clone());
                        }
                    }
                }
                // Raw pointers in the signature, args and return: every
                // position, by the fn's visibility and safety.
                if !foreign {
                    let site = counter_site(tcx, tcx.def_span(did));
                    let mut pointees = Vec::new();
                    for t in sig.inputs().iter().copied().chain(std::iter::once(sig.output())) {
                        raw_pointees(tcx, t, &mut pointees);
                    }
                    for p in pointees {
                        count_ptr_position(tcx, p, PtrSite::Fn { exported, safe }, &wrapped_c, site.clone(), &mut c, &mut sites);
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
            "{{\"crate\":\"{}\",\"code_lines\":{},\"total_stmts\":{},\"safe_fns_pub\":{},\"safe_fns_priv\":{},\"unsafe_blocks\":{},\"unsafe_block_stmts\":{},\"unsafe_block_lines\":{},\"unsafe_block_code_lines\":{},\"unsafe_blocks_wrapper_impl\":{},\"unsafe_blocks_ffi_export\":{},\"unsafe_fns\":{},\"unsafe_fns_pub\":{},\"unsafe_fns_priv\":{},\"unsafe_impls\":{},\"unsafe_traits\":{},\"ty_wrapper\":{},\"ty_wrapper_borrow_handles\":{},\"ty_wrapper_borrow_sanctioned\":{},\"ty_wrapper_borrow_smell\":{},\"ty_wrapper_borrow_body_smell\":{},\"ty_non_wrapper_borrow_pub_safe\":{},\"ty_non_wrapper_borrow_pub_unsafe\":{},\"ty_non_wrapper_borrow_priv_safe\":{},\"ty_non_wrapper_borrow_priv_unsafe\":{},\"raw_ptr_ty_pub_fields_pub\":{},\"raw_ptr_ty_pub_fields_priv\":{},\"raw_ptr_ty_priv\":{},\"raw_ptr_fn_pub_safe\":{},\"raw_ptr_fn_pub_unsafe\":{},\"raw_ptr_fn_priv_safe\":{},\"raw_ptr_fn_priv_unsafe\":{},\"raw_ptr_has_ty_wrapper\":{},\"raw_ptr_derefs\":{},\"raw_ptr_derefs_outside_impl\":{},\"void_ptr_ty_pub_fields_pub\":{},\"void_ptr_ty_pub_fields_priv\":{},\"void_ptr_ty_priv\":{},\"void_ptr_fn_pub_safe\":{},\"void_ptr_fn_pub_unsafe\":{},\"void_ptr_fn_priv_safe\":{},\"void_ptr_fn_priv_unsafe\":{},\"ty_field_proj_wrapped\":{},\"ty_field_proj_outside_impl\":{},\"ty_field_borrow_wrapped\":{},\"deref_impl_on_wrapper\":{},\"ffi_calls\":{},\"sites\":{}}}",
            krate, c.code_lines, c.total_stmts, c.safe_fns_pub, c.safe_fns_priv, c.unsafe_blocks, c.unsafe_block_stmts, c.unsafe_block_lines, c.unsafe_block_code_lines, c.unsafe_blocks_wrapper_impl, c.unsafe_blocks_ffi_export, c.unsafe_fns, c.unsafe_fns_pub, c.unsafe_fns_priv, c.unsafe_impls, c.unsafe_traits, c.ty_wrapper, c.ty_wrapper_borrow_handles, c.ty_wrapper_borrow_sanctioned, c.ty_wrapper_borrow_smell, c.ty_wrapper_borrow_body_smell, c.ty_non_wrapper_borrow_pub_safe, c.ty_non_wrapper_borrow_pub_unsafe, c.ty_non_wrapper_borrow_priv_safe, c.ty_non_wrapper_borrow_priv_unsafe, c.raw_ptr_ty_pub_fields_pub, c.raw_ptr_ty_pub_fields_priv, c.raw_ptr_ty_priv, c.raw_ptr_fn_pub_safe, c.raw_ptr_fn_pub_unsafe, c.raw_ptr_fn_priv_safe, c.raw_ptr_fn_priv_unsafe, c.raw_ptr_has_ty_wrapper, c.raw_ptr_derefs, c.raw_ptr_derefs_outside_impl, c.void_ptr_ty_pub_fields_pub, c.void_ptr_ty_pub_fields_priv, c.void_ptr_ty_priv, c.void_ptr_fn_pub_safe, c.void_ptr_fn_pub_unsafe, c.void_ptr_fn_priv_safe, c.void_ptr_fn_priv_unsafe, c.ty_field_proj_wrapped, c.ty_field_proj_outside_impl, c.ty_field_borrow_wrapped, c.deref_impl_on_wrapper, c.ffi_calls,
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
