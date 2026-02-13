```
# Task Checklist

## Phase 1: Planning and Architecture
- [x] Define new Stock Break logic (High Rotation + Zero Stock)
- [x] Design multi-store configuration system- [x] Backend Transformation
    - [x] Implement optimized SQL query `obtener_quiebres_directos` in `database.py`
    - [x] Refactor `monitorear_quiebres_stock` in `app.py`
- [/] UI Refinement & Cleanup (Stock Module)
    - [ ] Remove quantity filters (Critical/Medium/Low levels) from UI
    - [ ] Remove deposit configuration logic from Stock tab
    - [ ] Rename module UI components to consistent "Quiebre de Stock"
- [/] Logic Consolidation & Deprecation
    - [ ] Move/Remove stock break logic from TRA module
    - [ ] Create `pal/deprecated/` for legacy stock functions
    - [ ] Update background worker to iterate through all configured sedes
- [x] UI Card-based Admin System
    - [x] Implement `AdminMenu` card system (Configuraciones Globales)
    - [x] Implement sub-view navigation in `app.py`
- [x] Restoration of Sedes (Servidores)
    - [x] Create `SedesServidoresTab` for managing remote connections
    - [x] Integrate "Servidores" as a sub-module in Admin
- [/] Documentation & Registration
    - [x] Update `CHANGELOG.md` following `nexus.md` pattern
    - [ ] Update `walkthrough.md` with final refinements settings window

## Phase 3: Refinement & Verification
- [x] Fix `MA_DEPOSITOS` table name error (Change to `MA_DEPOSITO`) <!-- id: 5 -->
- [x] Move "Sedes y Stock" configuration to "Administration" module <!-- id: 6 -->
- [x] Support "Stock Break" logic with new configuration <!-- id: 7 -->
- [x] Verify background monitoring worker <!-- id: 8 -->

## Phase 4: UI Implementation (Popup)
- [ ] Create `pal/ui/stock_break_popup.py`
- [ ] Integrate popup triggering in `app.py`

## Phase 5: Verification
- [ ] Manual testing of configuration persistence
- [ ] Verify stock break alerts respect configured warehouses
- [ ] Deprecate old stock logic
