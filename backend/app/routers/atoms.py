from fastapi import APIRouter, HTTPException
from app.db.database import get_all_atoms, get_atom_by_id, search_atoms, get_atoms_by_category, get_all_bond_rules, get_all_risk_tags

router = APIRouter(prefix="/atoms", tags=["atoms"])


@router.get("")
async def list_atoms():
    return get_all_atoms()


@router.get("/search")
async def search(q: str):
    return search_atoms(q)


@router.get("/category/{category}")
async def by_category(category: str):
    return get_atoms_by_category(category)


@router.get("/{atom_id}")
async def get_atom(atom_id: str):
    atom = get_atom_by_id(atom_id)
    if not atom:
        raise HTTPException(status_code=404, detail="Atom not found")
    return atom


@router.get("/meta/bond-rules")
async def bond_rules():
    return get_all_bond_rules()


@router.get("/meta/risk-tags")
async def risk_tags():
    return get_all_risk_tags()
