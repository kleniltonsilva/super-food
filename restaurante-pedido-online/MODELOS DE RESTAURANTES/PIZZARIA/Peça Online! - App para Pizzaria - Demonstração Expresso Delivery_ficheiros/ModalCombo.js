let modalComboCurrent = null;

class ModalCombo{
  constructor(title, description, imageId, imageName, comboData, comboStatus = "new") {
    this.title = title;
    this.description = description || "";
    this.imageId = imageId || '';
    this.imageName = imageName || '';
    this.domainImage = 'https://static.expressodelivery.com.br/imagens/banners';
    this.baseClass = 'component_modal_combo';
    this.comboData = comboData;
    this.comboStatus = comboStatus;
  }

  getRender(){
    return `
      <input type="hidden" id="comboData" value='${JSON.stringify(this.comboData)}'>
      <input type="hidden" id="comboStatus" value='${this.comboStatus}'>
      <div class="headModalCombo">
        <h4 class="${this.baseClass}_modal_title">Adicionar ao Pedido</h4>
        <div class="hideModal">
          <i class="material-icons">close</i>
        </div>
      </div>
      <div class="contentModalCombo">
        <div class="${this.baseClass}_div_infos">
          <div class="${this.baseClass}_img">
            <img src="${this.domainImage}/${this.imageId}/${this.imageName}">
          </div>
          <h4 class="${this.baseClass}_title">${this.title}</h4>
          <p class="${this.baseClass}_description">${this.description}</p>
        </div>
        <div class="${this.baseClass}_items">
          <div class="list_items_combo">
          </div>
        </div>
      </div>
      <div class="footerModalCombo">
        <button class="mdl-button mdl-js-button btninativo" id="btn_finalizar_combo">
          <i class="material-icons">shopping_cart</i> Adicionar ao Pedido
          <span class="mdl-button__ripple-container"><span class="mdl-ripple"></span></span>
        </button>
      </div>
    `
  }

  updateHashDataCombo(hash){
    this.comboData["data_hash"] = hash;
    $('#comboData').val(JSON.stringify(this.comboData));
    if (comboItems) {
      comboItems = comboItems.map(x => {
        const data = JSON.parse(x['comboData']);
        data["data_hascombo"] = hash;
        x['comboData'] = JSON.stringify(data);
        return x;
      })
    }
  }
}