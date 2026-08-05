// DSM desktop app registration (floating window, ARC Control-style).
//
// This is what actually produces a resizable/maximizable window on the
// DSM desktop instead of navigating to a bare URL - the previous
// "ui/config" alone (a `.url`-type entry) was not sufficient. Modeled
// directly on AuxXxilium/arc-control's dsm-wrapper.js: DSM's app loader
// resolves `dsmappname` in INFO to an Ext.define'd class here, keyed by
// this exact file name in `ui/config`'s "dsm-wrapper.js" section.
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
                width: 900,
                height: 650,
                minWidth: 600,
                minHeight: 400,
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
    },
    onOpen: function (info) {
        this.callParent([info]);
    },
    onRequest: function (info) {
        this.onOpen(info);
    },
});
