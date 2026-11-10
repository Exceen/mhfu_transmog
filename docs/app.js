(function () {
    'use strict';

    // ── Constants ────────────────────────────────────────────────────────────

    const CWCHEAT_BASE = 0x08800000;
    const PSP_MAX_LINES = 30; // real PSP CWCheat: max lines per cheat, title line included
    const SLOT_NAMES = ['head', 'chest', 'arms', 'waist', 'legs'];
    const SLOT_LABELS = { head: 'Head', chest: 'Chest', arms: 'Arms', waist: 'Waist', legs: 'Legs' };
    const FORMAT_KEY = 'mhfu-transmog-format';

    // ── State ────────────────────────────────────────────────────────────────

    let DATA = null;
    let ONLINE = null;
    let currentMode = 'instructions';
    let outputBlocks = [];   // [{title, lines}]
    let outputRaw = '';
    let outputNote = null;   // string, or function(format) -> string
    let outputFormat = readFormat();

    // ── DOM refs ─────────────────────────────────────────────────────────────

    const modePanel = document.getElementById('mode-panel');
    const outputPanel = document.getElementById('output-panel');
    const outputSummary = document.getElementById('output-summary');
    const outputCodes = document.getElementById('output-codes');
    const outputInfo = document.getElementById('output-info');
    const formatToggle = document.getElementById('format-toggle');
    const btnCopy = document.getElementById('btn-copy');
    const btnDownload = document.getElementById('btn-download');
    const btnNew = document.getElementById('btn-new');
    const loadingOverlay = document.getElementById('loading-overlay');

    // ── Data Loading ─────────────────────────────────────────────────────────

    async function loadData() {
        try {
            const resp = await fetch('transmog_data.json');
            if (!resp.ok) throw new Error('Failed to load transmog_data.json');
            DATA = await resp.json();
        } catch (err) {
            loadingOverlay.innerHTML = '<p style="color:var(--red)">Failed to load equipment data. Please reload the page.</p>';
            return;
        }
        try {
            const resp = await fetch('online_codes.json');
            if (resp.ok) ONLINE = await resp.json();
        } catch (err) {
            ONLINE = null; // the Online tab explains that the codes are missing
        }
        loadingOverlay.classList.add('hidden');
        initModeTabs();
        initFormatToggle();
        renderMode('instructions');
    }

    // ── Utility ──────────────────────────────────────────────────────────────

    function displayName(names) {
        return names && names.length ? names[names.length - 1] : '???';
    }

    function hex(n, width) {
        return (n >>> 0).toString(16).toUpperCase().padStart(width, '0');
    }

    function variantLabel(variant, index, setNames) {
        var names = variant.names;
        if (names && names.length) {
            return names.length > 1 ? names[names.length - 1] : names[0];
        }
        if (setNames && setNames.length >= 2) {
            return index === 0 ? setNames[0] : setNames[setNames.length - 1];
        }
        return 'Variant ' + (index + 1);
    }

    function hasGenderDiff(targetSet) {
        if (!targetSet || !targetSet.variants) return false;
        return targetSet.variants.some(function (v) { return v.model_m !== v.model_f; });
    }

    function escapeHtml(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function readFormat() {
        try {
            return localStorage.getItem(FORMAT_KEY) === 'psp' ? 'psp' : 'ppsspp';
        } catch (e) {
            return 'ppsspp';
        }
    }

    function saveFormat(fmt) {
        try { localStorage.setItem(FORMAT_KEY, fmt); } catch (e) { /* private mode etc. */ }
    }

    // ── Item Builders ────────────────────────────────────────────────────────

    function buildWeaponItems(typeFilter) {
        var items = [];
        for (var modelStr in DATA.weapons) {
            var w = DATA.weapons[modelStr];
            if (typeFilter && w.type !== typeFilter) continue;
            items.push({ names: w.names, entries: w.entries, model: modelStr, type: w.type || '?', gunner: !!w.gunner });
        }
        items.sort(function (a, b) {
            return (a.names[0] || '').toLowerCase().localeCompare((b.names[0] || '').toLowerCase());
        });
        return items;
    }

    function buildArmorItems(slot) {
        var sets = DATA.armor[slot].sets;
        var items = sets.filter(function (s) {
            return !(s.names.length === 1 && s.names[0] === 'Nothing Equipped');
        });
        items.sort(function (a, b) {
            return (a.names[0] || '').toLowerCase().localeCompare((b.names[0] || '').toLowerCase());
        });
        return items;
    }

    // ── Code Generation ──────────────────────────────────────────────────────

    function genWeaponCodes(sourceWeapon, targetWeapon) {
        // Bowguns and bows have their own table (entries = equipment IDs).
        var gunner = sourceWeapon.gunner;
        var weaponBase = parseInt(gunner ? DATA.gunner_table_base : DATA.weapon_table_base, 16);
        var entrySize = gunner ? DATA.gunner_entry_size : DATA.weapon_entry_size;
        var modelOffset = gunner ? DATA.gunner_model_offset : DATA.weapon_model_offset;
        var targetModel = parseInt(targetWeapon.model);
        var lines = [];
        for (var i = 0; i < sourceWeapon.entries.length; i++) {
            var entryIdx = sourceWeapon.entries[i];
            var modelAddr = weaponBase + entryIdx * entrySize + modelOffset;
            lines.push('_L 0x1' + hex(modelAddr - CWCHEAT_BASE, 7) + ' 0x0000' + hex(targetModel, 4));
        }
        return lines;
    }

    // Returns model lines plus the pigment-flag lines (armor entry byte +19) for both
    // "enable" (2) and "disable" (0); the caller picks one or neither.
    function genArmorCodes(slot, sourceSet, targetSet, forceVariant, swapGender) {
        var tableBase = parseInt(DATA.armor[slot].table_base, 16);
        var entrySize = DATA.armor_entry_size;
        var modelLines = [];
        var pigmentOn = [];
        var pigmentOff = [];

        var srcVariants = sourceSet.variants;
        var tgtVariants = targetSet === null
            ? srcVariants.map(function () { return { model_m: 0, model_f: 0 }; })
            : targetSet.variants;

        for (var vi = 0; vi < srcVariants.length; vi++) {
            var srcV = srcVariants[vi];
            var tgtV;
            if (forceVariant !== null && forceVariant !== undefined) {
                tgtV = tgtVariants[forceVariant];
            } else {
                tgtV = vi < tgtVariants.length ? tgtVariants[vi] : tgtVariants[0];
            }
            var m = tgtV.model_m & 0xFFFF;
            var f = tgtV.model_f & 0xFFFF;
            var value = (swapGender ? ((m << 16) | f) : ((f << 16) | m)) >>> 0;

            for (var j = 0; j < srcV.eids.length; j++) {
                var entryAddr = tableBase + srcV.eids[j] * entrySize;
                modelLines.push('_L 0x2' + hex(entryAddr - CWCHEAT_BASE, 7) + ' 0x' + hex(value, 8));
                var pigAddr = hex(entryAddr + 19 - CWCHEAT_BASE, 7);
                pigmentOn.push('_L 0x0' + pigAddr + ' 0x00000002');
                pigmentOff.push('_L 0x0' + pigAddr + ' 0x00000000');
            }
        }
        return { modelLines: modelLines, pigmentOn: pigmentOn, pigmentOff: pigmentOff };
    }

    function armorLines(result, pigmentMode) {
        if (pigmentMode === 'enable') return result.modelLines.concat(result.pigmentOn);
        if (pigmentMode === 'disable') return result.modelLines.concat(result.pigmentOff);
        return result.modelLines;
    }

    function genUniversalInvisibleCodes(slot) {
        var tableBase = parseInt(DATA.armor[slot].table_base, 16);
        var entrySize = DATA.armor_entry_size;
        var lines = [];
        var sets = DATA.armor[slot].sets;
        for (var i = 0; i < sets.length; i++) {
            for (var vi = 0; vi < sets[i].variants.length; vi++) {
                var variant = sets[i].variants[vi];
                if (variant.model_m === 0 && variant.model_f === 0) continue;
                for (var j = 0; j < variant.eids.length; j++) {
                    var entryAddr = tableBase + variant.eids[j] * entrySize;
                    lines.push('_L 0x2' + hex(entryAddr - CWCHEAT_BASE, 7) + ' 0x00000000');
                }
            }
        }
        return lines;
    }

    // ── Output Panel ─────────────────────────────────────────────────────────

    // PPSSPP: one cheat per block. Real PSP: blocks longer than PSP_MAX_LINES are split
    // into numbered parts. Line order is kept, so code that must come last stays last.
    function formatBlocks(blocks, fmt) {
        var out = [];
        blocks.forEach(function (b) {
            if (fmt !== 'psp' || b.lines.length <= PSP_MAX_LINES - 1) {
                out.push('_C1 ' + b.title + '\n' + b.lines.join('\n'));
                return;
            }
            var per = PSP_MAX_LINES - 1;
            var parts = Math.ceil(b.lines.length / per);
            for (var p = 0; p < parts; p++) {
                out.push('_C1 ' + b.title + ' ' + (p + 1) + '/' + parts + '\n' +
                    b.lines.slice(p * per, (p + 1) * per).join('\n'));
            }
        });
        return out.join('\n\n');
    }

    function showOutput(blocks, summary, note) {
        outputBlocks = blocks;
        outputSummary.textContent = summary || '';
        outputNote = note || null;
        outputPanel.classList.remove('hidden');
        renderOutput();
        outputPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function renderOutput() {
        outputRaw = formatBlocks(outputBlocks, outputFormat);

        var html = '';
        var rawLines = outputRaw.split('\n');
        for (var i = 0; i < rawLines.length; i++) {
            var line = rawLines[i];
            if (line.startsWith('_C')) {
                html += '<span class="line-title">' + escapeHtml(line) + '</span>\n';
            } else if (line.trim() === '') {
                html += '\n';
            } else {
                html += '<span class="line-code">' + escapeHtml(line) + '</span>\n';
            }
        }
        outputCodes.innerHTML = html;

        var totalLines = rawLines.filter(function (l) { return l.startsWith('_L '); }).length;
        var cheats = rawLines.filter(function (l) { return l.startsWith('_C'); }).length;
        var info = totalLines + ' cheat line' + (totalLines !== 1 ? 's' : '') + ' in ' +
            cheats + ' cheat' + (cheats !== 1 ? 's' : '');
        if (outputFormat === 'psp' && cheats > outputBlocks.length) {
            info += ' — enable all parts';
        }
        outputInfo.textContent = info;

        var note = typeof outputNote === 'function' ? outputNote(outputFormat) : outputNote;
        var noteEl = document.getElementById('output-note');
        noteEl.innerHTML = note || '';
        noteEl.classList.toggle('hidden', !note);

        // Offline codes only change your own game: point to the online codes.
        document.getElementById('online-hint').classList.toggle('hidden', currentMode === 'online');
    }

    function hideOutput() {
        outputPanel.classList.add('hidden');
        outputBlocks = [];
        outputRaw = '';
    }

    function initFormatToggle() {
        var btns = formatToggle.querySelectorAll('button');
        function sync() {
            for (var i = 0; i < btns.length; i++) {
                btns[i].classList.toggle('active', btns[i].getAttribute('data-format') === outputFormat);
            }
        }
        formatToggle.addEventListener('click', function (e) {
            var btn = e.target.closest('button');
            if (!btn) return;
            outputFormat = btn.getAttribute('data-format');
            saveFormat(outputFormat);
            sync();
            if (outputBlocks.length) renderOutput();
        });
        sync();
    }

    function copyToClipboard(text, btn) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(function () { flashCopied(btn); });
        } else {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            flashCopied(btn);
        }
    }

    function flashCopied(btn) {
        var orig = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(function () {
            btn.textContent = orig;
            btn.classList.remove('copied');
        }, 1500);
    }

    btnCopy.addEventListener('click', function () {
        copyToClipboard(outputRaw, btnCopy);
    });

    btnDownload.addEventListener('click', function () {
        var blob = new Blob([outputRaw + '\n'], { type: 'text/plain' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'transmog_codes.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    btnNew.addEventListener('click', function () {
        renderMode(currentMode);
        modePanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    // ── Equipment Selector Component ─────────────────────────────────────────

    function createSelector(container, items, options) {
        options = options || {};
        var allowInvisible = options.allowInvisible || false;
        var presetSearch = options.presetSearch || '';
        var onSelect = options.onSelect || function () {};
        var selected = null;
        var invisibleSelected = false;
        var filtered = items;

        container.innerHTML =
            '<input type="text" class="search-input" placeholder="Search by name..." value="' + escapeHtml(presetSearch) + '">' +
            '<div class="item-list"></div>' +
            '<div class="item-count"></div>' +
            '<div class="selection-display">Selected: <span class="dim">none</span></div>';

        var searchInput = container.querySelector('.search-input');
        var itemList = container.querySelector('.item-list');
        var itemCount = container.querySelector('.item-count');
        var selectionDisplay = container.querySelector('.selection-display');

        function renderItems(filter) {
            if (filter) {
                var term = filter.toLowerCase();
                filtered = items.filter(function (item) {
                    return item.names.some(function (n) { return n.toLowerCase().indexOf(term) !== -1; });
                });
            } else {
                filtered = items;
            }

            var html = '';
            if (allowInvisible) {
                html += '<div class="item invisible-option' + (invisibleSelected ? ' selected' : '') + '" data-index="invisible">** Invisible **</div>';
            }
            if (filtered.length === 0) {
                html += '<div class="no-results">No results found</div>';
            } else {
                for (var i = 0; i < filtered.length; i++) {
                    var item = filtered[i];
                    html += '<div class="item' + (selected === item ? ' selected' : '') + '" data-index="' + i + '">' + escapeHtml(item.names.join(' / ')) + '</div>';
                }
            }
            itemList.innerHTML = html;
            itemCount.textContent = filtered.length + ' item' + (filtered.length !== 1 ? 's' : '');
        }

        function updateSelectionDisplay() {
            if (invisibleSelected) {
                selectionDisplay.innerHTML = 'Selected: <span class="invisible-name">Invisible</span>';
            } else if (selected) {
                selectionDisplay.innerHTML = 'Selected: <span class="selected-name">' + escapeHtml(selected.names.join(' / ')) + '</span>';
            } else {
                selectionDisplay.innerHTML = 'Selected: <span class="dim">none</span>';
            }
        }

        itemList.addEventListener('click', function (e) {
            var target = e.target.closest('.item');
            if (!target) return;
            var idx = target.getAttribute('data-index');
            if (idx === 'invisible') {
                selected = null;
                invisibleSelected = true;
                onSelect(null);
            } else {
                selected = filtered[parseInt(idx)];
                invisibleSelected = false;
                onSelect(selected);
            }
            var allItems = itemList.querySelectorAll('.item');
            for (var j = 0; j < allItems.length; j++) allItems[j].classList.remove('selected');
            target.classList.add('selected');
            updateSelectionDisplay();
        });

        var debounceTimer;
        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () { renderItems(searchInput.value); }, 100);
        });

        renderItems(presetSearch);
    }

    // ── Shared armor options (variant, gender, pigment) ──────────────────────

    function disabledOptionHtml(label) {
        return '<div class="option-group disabled"><div class="option-group-label">' + label +
            '</div><p class="dim option-placeholder">Select a target armor to configure</p></div>';
    }

    // Renders the variant/gender option groups for a target into `container` and
    // writes the choices into `state.forceVariant` / `state.swapGender`.
    function renderTargetOptions(container, target, isInvisible, state, prefix) {
        state.forceVariant = null;
        state.swapGender = false;

        var vHtml = disabledOptionHtml('Variant');
        var gHtml = disabledOptionHtml('Gender');

        if (!isInvisible && target) {
            if (target.variants && target.variants.length >= 2) {
                var setNames = target.names || [];
                var l0 = escapeHtml(variantLabel(target.variants[0], 0, setNames));
                var l1 = escapeHtml(variantLabel(target.variants[1], 1, setNames));
                vHtml =
                    '<div class="option-group">' +
                        '<div class="option-group-label">Variant</div>' +
                        '<label><input type="radio" name="' + prefix + 'variant" value="match" checked> Match armor type <span class="option-detail">(' + l0 + ' -> ' + l0 + ', ' + l1 + ' -> ' + l1 + ')</span></label>' +
                        '<label><input type="radio" name="' + prefix + 'variant" value="0"> ' + l0 + ' <span class="option-detail">(all pieces)</span></label>' +
                        '<label><input type="radio" name="' + prefix + 'variant" value="1"> ' + l1 + ' <span class="option-detail">(all pieces)</span></label>' +
                    '</div>';
            } else {
                vHtml = '';
            }
            if (hasGenderDiff(target)) {
                gHtml =
                    '<div class="option-group">' +
                        '<div class="option-group-label">Gender</div>' +
                        '<label><input type="radio" name="' + prefix + 'gender" value="default" checked> Default</label>' +
                        '<label><input type="radio" name="' + prefix + 'gender" value="swap"> Opposite gender model</label>' +
                    '</div>';
            } else {
                gHtml = '';
            }
        }

        container.innerHTML = vHtml + gHtml;

        container.querySelectorAll('input[name="' + prefix + 'variant"]').forEach(function (r) {
            r.addEventListener('change', function () {
                state.forceVariant = this.value === 'match' ? null : parseInt(this.value);
            });
        });
        container.querySelectorAll('input[name="' + prefix + 'gender"]').forEach(function (r) {
            r.addEventListener('change', function () {
                state.swapGender = this.value === 'swap';
            });
        });
    }

    function pigmentOptionHtml(name) {
        return '<div class="option-group">' +
            '<div class="option-group-label">Pigment</div>' +
            '<label><input type="radio" name="' + name + '" value="keep" checked> Unchanged <span class="option-detail">(the equipped armor decides)</span></label>' +
            '<label><input type="radio" name="' + name + '" value="enable"> Enable <span class="option-detail">(pigment color also on armor that normally can\'t be dyed; works best on S-series looks)</span></label>' +
            '<label><input type="radio" name="' + name + '" value="disable"> Disable <span class="option-detail">(never apply pigment color)</span></label>' +
        '</div>';
    }

    function pigmentChoice(name) {
        var checked = document.querySelector('input[name="' + name + '"]:checked');
        return checked ? checked.value : 'keep';
    }

    // ── Mode Tab Handling ────────────────────────────────────────────────────

    function selectMode(mode) {
        var tabs = document.querySelectorAll('.tab');
        for (var j = 0; j < tabs.length; j++) {
            tabs[j].classList.toggle('active', tabs[j].getAttribute('data-mode') === mode);
        }
        if (mode === currentMode) return;
        currentMode = mode;
        renderMode(mode);
    }

    function initModeTabs() {
        var tabs = document.querySelectorAll('.tab');
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].addEventListener('click', function () {
                selectMode(this.getAttribute('data-mode'));
            });
        }
        // in-page links like <a data-goto="online">
        document.addEventListener('click', function (e) {
            var link = e.target.closest('[data-goto]');
            if (!link) return;
            e.preventDefault();
            selectMode(link.getAttribute('data-goto'));
            document.getElementById('mode-tabs').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    function renderMode(mode) {
        modePanel.innerHTML = '';
        hideOutput();
        switch (mode) {
            case 'instructions': renderInstructionsMode(); break;
            case 'weapon': renderWeaponMode(); break;
            case 'armor-slot': renderArmorSlotMode(); break;
            case 'armor-set': renderArmorSetMode(); break;
            case 'universal-invisible': renderUniversalInvisibleMode(); break;
            case 'online': renderOnlineMode(); break;
        }
    }

    // ── Mode 0: Instructions ─────────────────────────────────────────────────

    function renderInstructionsMode() {
        modePanel.innerHTML =
            '<div class="section-title">Instructions</div>' +
            '<p class="hint">By using this website you can generate cheat codes (let\'s call them <i>transmog codes</i>) that change how your weapon and armor <b>look</b>. Stats, skills, slots and ' +
            'decorations always stay those of the gear you actually have equipped.</p>' +

            '<div class="callout">' +
                '<div class="callout-title">Playing with others? You need the Multiplayer codes too!</div>' +
                '<p>Transmog codes only change your own game. Without the <a href="#" data-goto="online">Multiplayer codes</a>, ' +
                'other players will keep seeing your normal equipment. Everyone who should see your transmog needs them as well.</p>' +
            '</div>' +

            '<div class="howto">' +
                '<div class="howto-step"><span class="step-num">1</span><div>' +
                    '<div class="howto-title">Generate your transmog</div>' +
                    '<p>Pick a tab: <a href="#" data-goto="weapon">Weapon</a>, ' +
                    '<a href="#" data-goto="armor-slot">Armor (Single Slot)</a>, <a href="#" data-goto="armor-set">Armor (Set)</a> ' +
                    'or <a href="#" data-goto="universal-invisible">Universal Invisible</a>. Choose the gear you have equipped ' +
                    '(<i>source</i>) and the gear whose look you want (<i>target</i>), then generate the codes.</p>' +
                '</div></div>' +
                '<div class="howto-step"><span class="step-num">2</span><div>' +
                    '<div class="howto-title">Add the codes and re-equip</div>' +
                    '<p>Copy the codes into your cheat file (see below), make sure to have them enabled, then unequip and re-equip the gear. ' +
                    'The game only loads the new look when the gear is changed or re-equipped.</p>' +
                    '<p>The idea is to generate codes that transform your whole equipment to a different look. You like two specific looks and ' +
                    'want to swap between them? Generate one code per look for the same equipped gear, then disable one, enable the other and re-equip!</p>' +
                '</div></div>' +
                '<div class="howto-step"><span class="step-num">3</span><div>' +
                    '<div class="howto-title">Your save data stays untouched</div>' +
                    '<p>Your equipment, stats and items are saved exactly as they are. ' +
                    'Nothing is patched permanently, neither the game nor its files. The codes only change the game while it is running. ' +
                    'Disable them and restart the game, and everything looks like before.</p>' +
                '</div></div>' +
                '<div class="howto-step"><span class="step-num">4</span><div>' +
                    '<div class="howto-title">Example needed?</div>' +
                    '<p>You wear the Mafumofu set and an Iron Katana, but want to look like the Black set (mixed Blademaster and Gunner pieces) with an invisible helmet and the Hellish Slasher?</p>' +
                    '<img class="example-gif" src="transmog.gif" width="480" height="272" alt="Transmog in action: equipment changing its look in-game">' +
                    '<div class="btn-row"><button class="btn btn-primary" id="example-toggle" aria-expanded="false" aria-controls="example-codes">Show example codes</button></div>' +
                    '<pre class="example-code hidden" id="example-codes">' +
                        '<span class="line-title">_C1 Weapon Transmog: Iron Katana -> Hellish Slasher</span>\n' +
                        '_L 0x101575B8 0x0000008A\n' +
                        '_L 0x101575D0 0x0000008A\n' +
                        '_L 0x101575E8 0x0000008A\n' +
                        '_L 0x1015B590 0x0000008A\n\n' +
                        '<span class="line-title">_C1 Armor Transmog: Mafumofu -> Black Mixed</span>\n' +
                        '_L 0x20162EB0 0x00000000\n' +
                        '_L 0x20167140 0x00300030\n' +
                        '_L 0x2016B218 0x002E002E\n' +
                        '_L 0x2016F228 0x00220024\n' +
                        '_L 0x201731E8 0x00230023' +
                    '</pre>' +
                '</div></div>' +
            '</div>' +

            '<div class="info-grid">' +
                '<div class="online-card">' +
                    '<div class="online-card-title">Where the codes go</div>' +
                    '<ul>' +
                        '<li><b>PPSSPP:</b> enable cheats in the settings, then paste into the cheats file (.ini). You can use the in-game cheat menu to edit it (start the game, go into the menu -> cheats -> edit cheat file). Reload the cheats by opening the cheats list or simply restart PPSSPP if you have any troubles.</li>' +
                        '<li><b>Real PSP:</b> add them to your CWCheat plugin\'s cheat file (.db): CWCheat only accepts ~30 lines per cheat, so long codes are split into parts (<code>1/4</code>, <code>2/4</code>, ...). Enable <b>all</b> parts. You can also use other cheat plugins like TempAR.</li>' +
                    '</ul>' +
                '</div>' +
                '<div class="online-card">' +
                    '<div class="online-card-title">Options</div>' +
                    '<ul>' +
                        '<li><b>Variant:</b> armor with Blademaster and Gunner versions can match your armor type or always use one version.</li>' +
                        '<li><b>Gender:</b> use the opposite gender\'s model if the target has different ones.</li>' +
                        '<li><b>Pigment:</b> keep it, enable dyeing on looks that normally can\'t be dyed (best on S-series), or disable it.</li>' +
                        '<li><b>Invisible:</b> hide a single piece, or every piece of a slot with Universal Invisible.</li>' +
                    '</ul>' +
                '</div>' +
                '<div class="online-card">' +
                    '<div class="online-card-title">Changing or removing a transmog</div>' +
                    '<ul>' +
                        '<li>To change a look, generate a new code for the same equipped gear, disable the old code, enable the new code, re-equip. You can have multiple codes running simultaneously for different gear (look X for armor A & look Y for armor B). Don\'t enable two codes for the same gear at once.</li>' +
                        '<li>To remove it, disable the code and restart the game. Disabling alone doesn\'t undo the change.</li>' +
                    '</ul>' +
                '</div>' +
                '<div class="online-card">' +
                    '<div class="online-card-title">Requirements</div>' +
                    '<ul>' +
                        '<li>Monster Hunter Freedom Unite. Only tested with the <a href="https://fucomplete.github.io" target="_blank" rel="noopener">FUComplete</a> patch v1.4.0; other versions may work but are untested.</li>' +
                        '<li>Multiplayer: everyone in the room should use the multiplayer codes in order to see each other\'s styles.</li>' +
                        '<li>Weapons can only take the look of another weapon of the same type.</li>' +
                    '</ul>' +
                '</div>' +
            '</div>' +

            '<p class="report-line">Something not working, or a look that\'s broken or wrong? ' +
                '<a href="https://github.com/Exceen/mhfu_transmog/issues" target="_blank" rel="noopener">Report an issue on GitHub</a></p>';

        var exampleBtn = document.getElementById('example-toggle');
        var exampleCodes = document.getElementById('example-codes');
        exampleBtn.addEventListener('click', function () {
            var show = exampleCodes.classList.toggle('hidden') === false;
            exampleBtn.textContent = show ? 'Hide example codes' : 'Show example codes';
            exampleBtn.setAttribute('aria-expanded', show ? 'true' : 'false');
        });
    }

    // ── Mode 1: Weapon Transmog ──────────────────────────────────────────────

    var WEAPON_TYPES = ['Great Sword', 'Long Sword', 'Sword & Shield', 'Dual Blades',
        'Hammer', 'Hunting Horn', 'Lance', 'Gunlance', 'Light Bowgun', 'Heavy Bowgun', 'Bow'];

    function renderWeaponMode() {
        modePanel.innerHTML =
            '<div class="section-title">Weapon Transmog</div>' +
            '<p class="hint">Pick a weapon type, then select the weapon you have equipped (source) and the weapon whose appearance you want (target). ' +
            'Targets are always the same weapon type, so a Great Sword stays a Great Sword.</p>' +
            '<div class="slot-picker" id="weapon-type-picker"></div>' +
            '<div id="weapon-content"></div>';

        var picker = document.getElementById('weapon-type-picker');
        picker.innerHTML = WEAPON_TYPES.filter(function (t) { return buildWeaponItems(t).length > 0; }).map(function (t) {
            var icon = 'images/w_' + t.toLowerCase().replace(/[^a-z]/g, '').replace('swordshield', 'swordandshield') + '.png';
            return '<button class="slot-btn" data-type="' + escapeHtml(t) + '"><img class="slot-icon" src="' + icon + '" alt="">' + escapeHtml(t) + '</button>';
        }).join('');

        picker.addEventListener('click', function (e) {
            var btn = e.target.closest('.slot-btn');
            if (!btn) return;
            var allBtns = picker.querySelectorAll('.slot-btn');
            for (var j = 0; j < allBtns.length; j++) allBtns[j].classList.remove('active');
            btn.classList.add('active');
            hideOutput();
            renderWeaponTypeFlow(document.getElementById('weapon-content'), btn.getAttribute('data-type'));
        });
    }

    function renderWeaponTypeFlow(container, type) {
        var typeItems = buildWeaponItems(type);

        container.innerHTML =
            '<div class="selector-row">' +
                '<div class="selector-col">' +
                    '<div class="selector-label">Source ' + escapeHtml(type) + ' (equipped)</div>' +
                    '<div id="weapon-source"></div>' +
                '</div>' +
                '<div class="selector-col">' +
                    '<div class="selector-label">Target (visual) — ' + escapeHtml(type) + '</div>' +
                    '<div id="weapon-target"></div>' +
                '</div>' +
            '</div>' +
            '<div class="btn-row">' +
                '<button class="btn btn-primary" id="weapon-generate" disabled>Generate Codes</button>' +
            '</div>';

        var sourceItem = null, targetItem = null;

        function checkReady() {
            document.getElementById('weapon-generate').disabled = !(sourceItem && targetItem);
        }

        createSelector(document.getElementById('weapon-source'), typeItems, {
            onSelect: function (item) { sourceItem = item; checkReady(); }
        });
        createSelector(document.getElementById('weapon-target'), typeItems, {
            onSelect: function (item) { targetItem = item; checkReady(); }
        });
        checkReady();

        document.getElementById('weapon-generate').addEventListener('click', function () {
            if (!sourceItem || !targetItem) return;
            var srcName = displayName(sourceItem.names);
            var tgtName = displayName(targetItem.names);
            showOutput([{ title: 'Weapon Transmog: ' + srcName + ' -> ' + tgtName, lines: genWeaponCodes(sourceItem, targetItem) }],
                srcName + ' -> ' + tgtName);
        });
    }

    // ── Mode 2: Armor (Single Slot) ──────────────────────────────────────────

    function renderArmorSlotMode() {
        modePanel.innerHTML =
            '<div class="section-title">Armor Transmog (Single Slot)</div>' +
            '<p class="hint">Select an armor slot, then choose source and target armor.</p>' +
            '<div class="slot-picker" id="slot-picker"></div>' +
            '<div id="armor-slot-content"></div>';

        renderSlotPicker(document.getElementById('slot-picker'), function (slot) {
            renderSingleSlotFlow(document.getElementById('armor-slot-content'), slot);
        });
    }

    function renderSlotPicker(container, onSelect) {
        var html = '';
        for (var i = 0; i < SLOT_NAMES.length; i++) {
            html += '<button class="slot-btn" data-slot="' + SLOT_NAMES[i] + '"><img class="slot-icon" src="images/a_' + SLOT_NAMES[i] + '.png" alt="">' + SLOT_LABELS[SLOT_NAMES[i]] + '</button>';
        }
        container.innerHTML = html;

        container.addEventListener('click', function (e) {
            var btn = e.target.closest('.slot-btn');
            if (!btn) return;
            var allBtns = container.querySelectorAll('.slot-btn');
            for (var j = 0; j < allBtns.length; j++) allBtns[j].classList.remove('active');
            btn.classList.add('active');
            onSelect(btn.getAttribute('data-slot'));
        });
    }

    function renderSingleSlotFlow(container, slot) {
        var items = buildArmorItems(slot);

        container.innerHTML =
            '<div class="selector-row">' +
                '<div class="selector-col">' +
                    '<div class="selector-label">Source ' + SLOT_LABELS[slot] + ' (equipped)</div>' +
                    '<div id="armor-source"></div>' +
                '</div>' +
                '<div class="selector-col">' +
                    '<div class="selector-label">Target ' + SLOT_LABELS[slot] + ' (visual)</div>' +
                    '<div id="armor-target"></div>' +
                '</div>' +
            '</div>' +
            '<div id="armor-options">' + disabledOptionHtml('Variant') + disabledOptionHtml('Gender') + '</div>' +
            pigmentOptionHtml('armor-pigment') +
            '<div class="btn-row">' +
                '<button class="btn btn-primary" id="armor-generate" disabled>Generate Codes</button>' +
            '</div>';

        var state = { source: null, target: null, isInvisible: false, forceVariant: null, swapGender: false };

        function checkReady() {
            document.getElementById('armor-generate').disabled = !(state.source && (state.target || state.isInvisible));
        }

        createSelector(document.getElementById('armor-source'), items, {
            onSelect: function (item) { state.source = item; checkReady(); }
        });

        createSelector(document.getElementById('armor-target'), items, {
            allowInvisible: true,
            onSelect: function (item) {
                state.target = item;
                state.isInvisible = item === null;
                renderTargetOptions(document.getElementById('armor-options'), state.target, state.isInvisible, state, 'slot-');
                checkReady();
            }
        });

        document.getElementById('armor-generate').addEventListener('click', function () {
            if (!state.source) return;
            var target = state.isInvisible ? null : state.target;
            var result = genArmorCodes(slot, state.source, target, state.forceVariant, state.swapGender);
            var srcName = displayName(state.source.names);
            var tgtName = state.isInvisible ? 'Invisible' : displayName(state.target.names);
            var suffix = state.isInvisible ? ' (invisible ' + SLOT_LABELS[slot].toLowerCase() + ')' : '';
            showOutput([{ title: 'Armor Transmog: ' + srcName + ' -> ' + tgtName + suffix, lines: armorLines(result, pigmentChoice('armor-pigment')) }],
                SLOT_LABELS[slot] + ': ' + srcName + ' -> ' + tgtName);
        });
    }

    // ── Mode 3: Armor (Set) ──────────────────────────────────────────────────

    function renderArmorSetMode() {
        modePanel.innerHTML =
            '<div class="section-title">Armor Transmog (Set)</div>' +
            '<p class="hint">Optional: enter a search term for your equipped set and for the look you want. It\'s pre-filled for every slot. Then select source and target for each armor slot.</p>' +
            '<div class="filter-row">' +
                '<div class="filter-col"><label>Source search filter</label><input type="text" id="set-source-filter" placeholder="e.g. Mafumofu"></div>' +
                '<div class="filter-col"><label>Target search filter</label><input type="text" id="set-target-filter" placeholder="e.g. Black"></div>' +
            '</div>' +
            pigmentOptionHtml('set-pigment') +
            '<div class="btn-row" style="margin-bottom:16px">' +
                '<button class="btn btn-primary" id="set-start">Start</button>' +
            '</div>' +
            '<div id="set-wizard"></div>';

        document.getElementById('set-start').addEventListener('click', function () {
            var sourceFilter = document.getElementById('set-source-filter').value.trim();
            var targetFilter = document.getElementById('set-target-filter').value.trim();
            this.disabled = true;
            document.getElementById('set-source-filter').disabled = true;
            document.getElementById('set-target-filter').disabled = true;
            var wizard = document.getElementById('set-wizard');
            runArmorSetWizard(wizard, sourceFilter, targetFilter);
            wizard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    function runArmorSetWizard(container, sourceFilter, targetFilter) {
        var results = [];
        var currentSlotIdx = 0;

        function renderStep() {
            if (currentSlotIdx >= SLOT_NAMES.length) {
                finishArmorSet();
                return;
            }
            var slot = SLOT_NAMES[currentSlotIdx];
            var progress = currentSlotIdx / SLOT_NAMES.length * 100;

            container.innerHTML =
                '<div class="wizard-header">' +
                    '<span class="wizard-step-label">Step ' + (currentSlotIdx + 1) + ' of ' + SLOT_NAMES.length + '</span>' +
                    '<div class="wizard-progress"><div class="wizard-progress-fill" style="width:' + progress + '%"></div></div>' +
                '</div>' +
                '<div class="wizard-slot-label">' + SLOT_LABELS[slot] + '</div>' +
                '<div class="selector-row">' +
                    '<div class="selector-col"><div class="selector-label">Source (equipped)</div><div id="wiz-source"></div></div>' +
                    '<div class="selector-col"><div class="selector-label">Target (visual)</div><div id="wiz-target"></div></div>' +
                '</div>' +
                '<div id="wiz-options">' + disabledOptionHtml('Variant') + disabledOptionHtml('Gender') + '</div>' +
                '<div class="btn-row">' +
                    '<button class="btn btn-primary" id="wizard-confirm" disabled>Confirm</button>' +
                    '<button class="btn btn-skip" id="wizard-skip">Skip ' + SLOT_LABELS[slot] + '</button>' +
                '</div>';

            var items = buildArmorItems(slot);
            var state = { source: null, target: null, isInvisible: false, forceVariant: null, swapGender: false };

            function checkReady() {
                document.getElementById('wizard-confirm').disabled = !(state.source && (state.target || state.isInvisible));
            }

            createSelector(document.getElementById('wiz-source'), items, {
                presetSearch: sourceFilter,
                onSelect: function (item) { state.source = item; checkReady(); }
            });
            createSelector(document.getElementById('wiz-target'), items, {
                allowInvisible: true,
                presetSearch: targetFilter,
                onSelect: function (item) {
                    state.target = item;
                    state.isInvisible = item === null;
                    renderTargetOptions(document.getElementById('wiz-options'), state.target, state.isInvisible, state, 'wiz-');
                    checkReady();
                }
            });

            document.getElementById('wizard-skip').addEventListener('click', function () {
                currentSlotIdx++;
                renderStep();
            });

            document.getElementById('wizard-confirm').addEventListener('click', function () {
                if (!state.source) return;
                var target = state.isInvisible ? null : state.target;
                results.push({
                    slot: slot,
                    result: genArmorCodes(slot, state.source, target, state.forceVariant, state.swapGender),
                    srcName: displayName(state.source.names),
                    tgtName: state.isInvisible ? 'Invisible' : displayName(state.target.names),
                    isInvisible: state.isInvisible
                });
                currentSlotIdx++;
                renderStep();
            });
        }

        function finishArmorSet() {
            if (results.length === 0) {
                container.innerHTML = '<p class="hint">No codes generated (all slots skipped).</p>';
                return;
            }

            var pigment = pigmentChoice('set-pigment');
            var allLines = [];
            var targetNames = {};
            var sourceNames = {};
            var invisibleSlots = [];

            results.forEach(function (r) {
                allLines = allLines.concat(armorLines(r.result, pigment));
                sourceNames[r.srcName] = true;
                if (r.isInvisible) invisibleSlots.push(SLOT_LABELS[r.slot].toLowerCase());
                else targetNames[r.tgtName] = true;
            });

            var tgtKeys = Object.keys(targetNames);
            var srcKeys = Object.keys(sourceNames);
            var tgtDisplay = tgtKeys.length === 1 ? tgtKeys[0] : (tgtKeys.length === 0 ? 'Invisible' : 'Custom');
            var srcDisplay = srcKeys.length === 1 ? srcKeys[0] : 'Mixed';

            var title = 'Armor Transmog: ' + srcDisplay + ' -> ' + tgtDisplay;
            if (invisibleSlots.length > 0) title += ' (invisible ' + invisibleSlots.join(', ') + ')';

            var summary = results.map(function (r) {
                return SLOT_LABELS[r.slot] + ': ' + r.srcName + ' -> ' + r.tgtName;
            }).join('\n');

            container.innerHTML =
                '<div class="wizard-header">' +
                    '<span class="wizard-step-label">Done</span>' +
                    '<div class="wizard-progress"><div class="wizard-progress-fill" style="width:100%"></div></div>' +
                '</div>';

            showOutput([{ title: title, lines: allLines }], summary);
        }

        renderStep();
    }

    // ── Mode 4: Universal Invisible ──────────────────────────────────────────

    function renderUniversalInvisibleMode() {
        modePanel.innerHTML =
            '<div class="section-title">Universal Invisible Slot</div>' +
            '<p class="hint">Makes every armor piece in the chosen slot invisible, whatever you have equipped there.</p>' +
            '<div class="slot-picker" id="invis-slot-picker"></div>';

        renderSlotPicker(document.getElementById('invis-slot-picker'), function (slot) {
            var lines = genUniversalInvisibleCodes(slot);
            showOutput([{ title: 'Universal Invisible ' + SLOT_LABELS[slot] + ' (' + lines.length + ' entries)', lines: lines }],
                SLOT_LABELS[slot] + ': ' + lines.length + ' entries set to invisible');
        });
    }

    // ── Mode 5: Multiplayer ──────────────────────────────────────────────────

    function renderOnlineMode() {
        if (!ONLINE || !ONLINE.cheats) {
            modePanel.innerHTML =
                '<div class="section-title">Multiplayer</div>' +
                '<p class="error-msg">online_codes.json could not be loaded.</p>';
            return;
        }
        var armor = ONLINE.cheats.armor;
        var weapon = ONLINE.cheats.weapon;

        modePanel.innerHTML =
            '<div class="section-title">Multiplayer</div>' +
            '<p class="hint">The transmog codes from the other tabs only change your own game. ' +
            'Add these codes so other players see your transmog too, and you see theirs.</p>' +
            '<div class="online-grid">' +
                '<div class="online-card">' +
                    '<div class="online-card-title">How it works</div>' +
                    '<ul>' +
                        '<li>Your game sends the models your transmog codes picked (and your pigment setting) along with your normal equipment data.</li>' +
                        '<li>Players <b>with</b> these codes see your transmog. Players <b>without</b> them see your real equipment, nothing breaks for them.</li>' +
                        '<li>Stats are never touched. Ideally everyone in the room should use the same game version (tested: FUComplete v1.4.0).</li>' +
                    '</ul>' +
                '</div>' +
                '<div class="online-card">' +
                    '<div class="online-card-title">Setup</div>' +
                    '<ol>' +
                        '<li>Keep your normal transmog codes enabled; these codes send what they set.</li>' +
                        '<li>Add the Multiplayer codes and enable them. No restart needed.</li>' +
                        '<li>After changing any codes, re-equip and change area (or rejoin) so others get the update.</li>' +
                    '</ol>' +
                '</div>' +
            '</div>' +
            '<div class="option-group">' +
                '<div class="option-group-label">Codes</div>' +
                '<label><input type="checkbox" id="online-armor" checked> ' + escapeHtml(armor.title) +
                    ' <span class="option-detail">(' + armor.lines.length + ' lines)</span></label>' +
                '<label><input type="checkbox" id="online-weapon" checked> ' + escapeHtml(weapon.title) +
                    ' <span class="option-detail">(' + weapon.lines.length + ' lines)</span></label>' +
            '</div>' +
            '<p class="hint">Both codes are independent: use either one or both.</p>' +
            '<div class="btn-row">' +
                '<button class="btn btn-primary" id="online-generate">Show Codes</button>' +
            '</div>';

        var armorBox = document.getElementById('online-armor');
        var weaponBox = document.getElementById('online-weapon');
        var btn = document.getElementById('online-generate');

        function checkReady() { btn.disabled = !(armorBox.checked || weaponBox.checked); }
        armorBox.addEventListener('change', checkReady);
        weaponBox.addEventListener('change', checkReady);

        btn.addEventListener('click', function () {
            var blocks = [];
            var names = [];
            if (armorBox.checked) { blocks.push({ title: armor.title, lines: armor.lines }); names.push('armor'); }
            if (weaponBox.checked) { blocks.push({ title: weapon.title, lines: weapon.lines }); names.push('weapon'); }
            showOutput(blocks, 'Multiplayer transmog: ' + names.join(' + '), function (fmt) {
                return fmt === 'psp'
                    ? 'Real PSP format: CWCheat allows at most 30 lines per cheat, so these codes are split into parts. Enable <b>every</b> part!'
                    : 'Playing on a real PSP? Select <b>Real PSP</b> above: CWCheat there allows at most 30 lines per cheat, so the codes have to be split into parts.';
            });
        });
    }

    // ── Init ─────────────────────────────────────────────────────────────────

    loadData();

})();
