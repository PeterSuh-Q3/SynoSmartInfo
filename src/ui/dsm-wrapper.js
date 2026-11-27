// DSM desktop app registration (floating window).
//
// This is what actually produces a resizable/maximizable window on the
// DSM desktop instead of navigating to a bare URL - the previous
// "ui/config" alone (a `.url`-type entry) was not sufficient. DSM's app
// loader resolves `dsmappname` in INFO to an Ext.define'd class here,
// keyed by this exact file name in `ui/config`'s "dsm-wrapper.js"
// section.
Ext.ns('PeterSuh.SynoSmartInfo');

Ext.define('PeterSuh.SynoSmartInfo.AppInstance', {
    extend: 'SYNO.SDS.AppInstance',
    appWindowName: 'PeterSuh.SynoSmartInfo.AppWindow',
    constructor: function () {
        this.callParent(arguments);
    },
});

Ext.define('PeterSuh.SynoSmartInfo.AppWindow', {
    extend: 'SYNO.SDS.AppWindow',
    constructor: function (config) {
        const cfg = Ext.apply(
            {
                resizable: true,
                maximizable: true,
                minimizable: true,
                width: 1200,
                height: 800,
                minWidth: 700,
                minHeight: 500,
                layout: 'fit',
                border: false,
                cls: 'syno-app-synosmartinfo-wrapper',
                items: [
                    {
                        xtype: 'box',
                        autoEl: {
                            tag: 'iframe',
                            src: '/webman/3rdparty/Synosmartinfo/index.html',
                            frameborder: '0',
                            style: 'width:100%; height:100%; border:none;',
                        },
                    },
                ],
            },
            config
        );
        this.callParent([cfg]);

        // Click-to-front for the iframe. A click inside an iframe goes to
        // the iframe's own document and never reaches DSM's window-
        // activation handler, so a partly covered window stays behind.
        // While this window is inactive the iframe is made click-through
        // (pointer-events:none); the click then lands on the Ext box
        // underneath, bubbles up as normal and DSM raises the window. Once
        // active, the iframe is interactive again.
        // DSM may already have rendered the window inside callParent, in
        // which case 'afterrender' has fired and would never be heard.
        if (this.rendered) {
            this.setupClickToFront();
        } else {
            this.on('afterrender', this.setupClickToFront, this, { single: true });
        }
        this.on('destroy', this.teardownClickToFront, this);
    },
    setupClickToFront: function () {
        if (this.sfSetActive) { return; }   // already set up
        const self = this;
        const frameBox = this.items && this.items.first();
        this.sfFrameDom = frameBox && frameBox.el ? frameBox.el.dom : null;
        if (!this.sfFrameDom) { return; }

        this.sfSetActive = function (active) {
            if (self.sfFrameDom) { self.sfFrameDom.style.pointerEvents = active ? '' : 'none'; }
        };
        this.on('activate', function () { this.sfSetActive(true); }, this);
        this.on('deactivate', function () { this.sfSetActive(false); }, this);
        // A mousedown inside our own window (outside the iframe) means it
        // is, or is about to be, the active one.
        this.el.on('mousedown', function () { this.sfSetActive(true); }, this);
        // Fallback in case activate/deactivate don't fire: a mousedown
        // anywhere else in the DSM desktop document means another window
        // or the desktop was clicked.
        this.sfDocMouseDown = function (ev) {
            if (self.el && !self.el.dom.contains(ev.getTarget())) { self.sfSetActive(false); }
        };
        Ext.getDoc().on('mousedown', this.sfDocMouseDown);
    },
    teardownClickToFront: function () {
        if (this.sfDocMouseDown) {
            Ext.getDoc().un('mousedown', this.sfDocMouseDown);
            this.sfDocMouseDown = null;
        }
        this.sfFrameDom = null;
    },
    onOpen: function (info) {
        this.callParent([info]);
    },
    onRequest: function (info) {
        this.onOpen(info);
    },
});
