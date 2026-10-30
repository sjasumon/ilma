/* Stable facade for the bank and service screen modules. */
window.IlmaCatalog={
 enter(tab){if(tab==='detail')window.IlmaBank.enter();else if(tab==='services')window.IlmaServices.enter();},
 reportReady(...args){return window.IlmaBank.reportReady(...args);},
 toggleWatch(...args){return window.IlmaBank.toggleWatch(...args);},
 openComparison(...args){return window.IlmaServices.openComparison(...args);},
 openBankServices(...args){return window.IlmaServices.openBankServices(...args);},
 listenLabel(){return window.IlmaServices.listenLabel();},
 relocalize(){if(currentTab==='detail')window.IlmaBank.relocalize();else if(currentTab==='services')window.IlmaServices.relocalize();}
};
