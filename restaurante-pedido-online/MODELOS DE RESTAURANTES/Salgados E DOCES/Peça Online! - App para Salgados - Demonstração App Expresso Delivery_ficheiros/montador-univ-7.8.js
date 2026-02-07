/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
let permite_obsmanual = 'N';
let item_tamanho = false;
let configComposicoesItemCombo = {};
let deviceED = 'desktop';
let finalizaPizzaAndamento = false;

localStorage.removeItem('ed_obsitem');
$(document).on('blur', '#obspedido', function(e){
  localStorage.setItem('ed_obsitem', $(this).val());
});

function hide_listaSabores(elemento) {
  if (!elemento.hasClass("noitemselected")) {
    var codclass = elemento.data("target-combo");
    $(".listadesaboresescolher." + codclass)
      .stop()
      .animate({ left: "-900px" }, 400);
    $(".esmaecer_montador." + codclass)
      .stop()
      .fadeOut(1000);
  }
}

function show_listaSabores(elemento) {
  var codclass = elemento.data("target-combo");
  $(".esmaecer_montador." + codclass).addClass("blackesm");
  $(".listadesaboresescolher." + codclass)
    .stop()
    .animate({ left: "0px" }, 400);
  $(".esmaecer_montador." + codclass)
    .stop()
    .fadeIn(1000);
}

function hide_listaIngredientes(elemento) {
  if (!elemento.hasClass("noitemselected")) {
    var codclass = elemento.data("target-combo");
    $(".listadeingredientes_opc." + codclass)
      .stop()
      .animate({ right: "-350px" }, 400);
    $(".esmaecer_montador." + codclass)
      .stop()
      .fadeOut(10);
    hide_listaObs(codclass);
    hide_listaMassa(codclass);
    hide_listaBorda(codclass);
    hide_listaComposicoes(codclass);
  }
}

function show_listaIngredientes(elemento) {
  var codclass = elemento.data("target-combo");
  $(".esmaecer_montador." + codclass).removeClass("blackesm");
  $(".listadeingredientes_opc." + codclass)
    .stop()
    .animate({ right: "0px" }, 400);
  $(".esmaecer_montador." + codclass)
    .stop()
    .fadeIn(10);
}

/* observações */
function hide_listaObs(cod) {
  $(".listadeobservacoes." + cod)
    .stop()
    .animate({ right: "-350px" }, 400);
}
function show_listaObs(elemento) {
  var codclass = elemento.data("target-combo");
  $(".esmaecer_montador." + codclass).removeClass("blackesm");
  $(".listadeobservacoes." + codclass)
    .stop()
    .animate({ right: "0px" }, 400);
  $(".esmaecer_montador." + codclass)
    .stop()
    .fadeIn(10);
}
/*
 *
 */

/* massa */
function hide_listaMassa(cod) {
  $(".listademassas." + cod)
    .stop()
    .animate({ right: "-350px" }, 400);
}
function show_listaMassa(elemento) {
  var codclass = elemento.data("target-combo");
  $(".esmaecer_montador." + codclass).removeClass("blackesm");
  $(".listademassas." + codclass)
    .stop()
    .animate({ right: "0px" }, 400);
  $(".esmaecer_montador." + codclass)
    .stop()
    .fadeIn(10);
}
/*
 *
 */

/* borda */
function hide_listaBorda(cod) {
  $(".listadebordas." + cod)
    .stop()
    .animate({ right: "-350px" }, 400);
}
function show_listaBorda(elemento) {
  var codclass = elemento.data("target-combo");
  $(".esmaecer_montador." + codclass).removeClass("blackesm");
  $(".listadebordas." + codclass)
    .stop()
    .animate({ right: "0px" }, 400);
  $(".esmaecer_montador." + codclass)
    .stop()
    .fadeIn(10);
}
/*
 *
*/

function show_listaComposicoes(elemento) {
  var codclass = elemento.data("target-combo");
  $(".esmaecer_montador." + codclass).removeClass("blackesm");
  $(".listadecomposicoes." + codclass)
    .stop()
    .animate({ right: "0px" }, 400);
  $(".esmaecer_montador." + codclass)
    .stop()
    .fadeIn(10);
}

function hide_listaComposicoes(cod) {
  $(".listadecomposicoes." + cod)
    .stop()
    .animate({ right: "-350px" }, 400);
}


function abrirListaSabores(elen) {
  var codtarget = elen.data("target-combo"); //data("combo-abatarget");
  var pedaco = elen.data("pdc");
  var confitem = $("#" + codtarget).data("combo-confitem");
  var htmlist = "";
  if (confitem == false) {
    var dadositem = $("#" + codtarget).data("dadositem");
    var sessao = dadositem.item_sessaoid;
    var codtamanho = dadositem.item_tamanhoid;
    var nsabores = get_saboresSessao(sessao);
    htmlist = reendListaSabores(nsabores, codtarget, codtamanho, pedaco, true);
  } else {
    htmlist = reendListaSabores(
      confitem.sabores,
      codtarget,
      confitem.tamanhos,
      pedaco,
      true
    );
  }
  $(".listadesaboresescolher." + codtarget).remove();
  $(".listadeingredientes_opc." + codtarget).remove();

  $(".esmaecer_montador." + codtarget).after(htmlist);
  $(".listadesaboresescolher." + codtarget).css("left", "-900px");

  show_listaSabores(elen);

  $(".nano").nanoScroller();
}

async function finalizaCombo() {
  let targetItemValidation = $(".abacombo.ativa").data("combo-abatarget");
  let dados = $("#" + targetItemValidation).data("dadosdoitematual");
  let configCombo = $("#" + targetItemValidation).data("combo-confitem");
  if (configCombo) {
    configComposicoesItemCombo = configCombo.opcionais.hasOwnProperty('COMPOSICOES') ? configCombo.opcionais['COMPOSICOES'] : {};
  }
  if (dados && (dados.length > 0 || typeof dados == 'object')) {
    const setCompositions = await setCompositionsItemCombo(dados.data_hash);
    if (!setCompositions) return;
  }

  var combo_info = $("#montador_combo").data("combo-infos");
  var hash = $("#montador_combo").data("combo-hash");
  var id_combo = combo_info.combo_id;
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/finalizacombo/",
    data: { data_hash: hash, data_cod: id_combo},
    dataType: "json",
  }).done(function (msg) {
    hideLoading();
    if (msg.res === true) {
      if (fbp_configurado == true && combo_info != undefined && combo_info != null) {
        fbq("track", "AddToCart", {
            content_name: combo_info.combo_nome,
            content_category: "COMBO " + combo_info.combo_modelo,
            content_ids: [combo_info.combo_id],
            content_type: "product",
            value: 0,
            currency: "BRL",
          },
          {
            eventID: facebookEventID
          }
        );
      }

      if (tiktokpixel_configurado == true && combo_info != undefined && combo_info != null) {
        ttq.track('AddToCart', {
          content_name: combo_info.combo_nome,
          content_category: "COMBO " + combo_info.combo_modelo,
          content_id: [combo_info.combo_id],
          content_type: "product",
          value: 0,
          currency: "BRL",
        });
      }

      $("#montDorCombo").modal("hide");
      get_resumoPedido();
      $(".fechar_modal").show();

      resetArrayCompositionsItem();

      showMsgItemAdd();
    } else if (msg.res === false) {
      if(msg.data!=undefined){
        if(msg.data.codconfitem!=undefined){
          $(".cont_abascombo").each(function(i,l){
            var constlid = l.id;
            var dtabaconfig = $("#"+constlid).data("combo-confitem");
            if(dtabaconfig.codconfig==msg.data.codconfitem){
              $("#montador_combo .abas_combo a[data-combo-abatarget='"+constlid+"']").trigger("click");
              if (msg.msg != undefined) {
                Swal({
                  type: "info",
                  title: msg.msg,
                  text: "Essa opção é obrigatória",
                  onClose: () => {
                      $(".btnbrd_montmodal."+constlid).trigger("click");
                  },
                });
              }
            }
          })
        }
      }else{
        if (msg.msg != undefined){
            Swal({
                type: "info",
                title: "Atenção!",
                text: msg.msg,
            });
        }
      }

      if(msg.erro_msg != undefined){
        Swal({
            type: "error",
            title: "Oops..",
            html: msg.erro_msg
        }); 
      } 
    } else {

    }
  });
}

function get_observacoesdasessao(codsessao, codtamanho) {
  var cntobs = observacoes_itens.length;
  var arrobs = [];
  var k = 0;
  for (var i = 0; i < cntobs; i++) {
    if (observacoes_itens[i].observacoes_sessaoid == codsessao) {
      if (
        observacoes_itens[i].observacoes_precotamanho != false &&
        observacoes_itens[i].observacoes_precotamanho != undefined
      ) {
        var conttmobs = observacoes_itens[i].observacoes_precotamanho.length;
        for (var g = 0; g < conttmobs; g++) {
          if (
            observacoes_itens[i].observacoes_precotamanho[g]
              .precotamannho_tamanhoid == codtamanho
          ) {
            arrobs[k] = observacoes_itens[i];
            arrobs[k]["preco"] =
              observacoes_itens[i].observacoes_precotamanho[
                g
              ].precotamannho_preco;
            k++;
          }
        }
      }
    }
  }
  return arrobs.length > 0 ? arrobs : false;
}

function get_massasdasessao(codsessao, codtamanho) {
  var cntobs = massas_itens.length;
  var arrobs = [];
  var k = 0;
  for (var i = 0; i < cntobs; i++) {
    if (massas_itens[i].massa_sessaoid == codsessao) {
      if (
        massas_itens[i].massa_precotamanho != false &&
        massas_itens[i].massa_precotamanho != undefined
      ) {
        var conttmobs = massas_itens[i].massa_precotamanho.length;
        for (var g = 0; g < conttmobs; g++) {
          if (
            massas_itens[i].massa_precotamanho[g].precotamannho_tamanhoid ==
            codtamanho
          ) {
            arrobs[k] = massas_itens[i];
            arrobs[k]["preco"] =
              massas_itens[i].massa_precotamanho[g].precotamannho_preco;
            arrobs[k]["massa_preco"] =
              massas_itens[i].massa_precotamanho[g].precotamannho_preco;
            k++;
          }
        }
      }
    }
  }
  return arrobs.length > 0 ? arrobs : false;
}

function get_bordadasessao(codsessao, codtamanho) {
  var cntobs = bordas_itens.length;
  var arrobs = [];
  var k = 0;
  for (var i = 0; i < cntobs; i++) {
    if (bordas_itens[i].borda_sessaoid == codsessao) {
      if (
        bordas_itens[i].borda_precotamanho != false &&
        bordas_itens[i].borda_precotamanho != undefined
      ) {
        var conttmobs = bordas_itens[i].borda_precotamanho.length;
        for (var g = 0; g < conttmobs; g++) {
          if (
            bordas_itens[i].borda_precotamanho[g].precotamannho_tamanhoid ==
            codtamanho
          ) {
            arrobs[k] = bordas_itens[i];
            arrobs[k]["preco"] =
              bordas_itens[i].borda_precotamanho[g].precotamannho_preco;
            arrobs[k]["borda_preco"] =
              bordas_itens[i].borda_precotamanho[g].precotamannho_preco;
            k++;
          }
        }
      }
    }
  }
  return arrobs.length > 0 ? arrobs : false;
}

function get_observacaoexist(obsusando, cod) {
  if (obsusando != false) {
    var cntobs = obsusando.length;
    for (var h = 0; h < cntobs; h++) {
      if (obsusando[h].item_observacaoid == cod) {
        return true;
      }
    }
  }
  return false;
}

function get_bordaexist(bordausando, cod) {
  if (bordausando != false) {
    var cntobs = bordausando.length;
    for (var h = 0; h < cntobs; h++) {
      if (bordausando[h].item_bordaid == cod) {
        return true;
      }
    }
  }
  return false;
}

function get_massaexist(massausando, cod) {
  if (massausando != false) {
    if (massausando.item_massaid == cod) {
      return true;
    }
  }
  return false;
}

function rendListaObs(elemento) {
  var codtarget = elemento.data("target-combo");
  var dadositemmontagem = $("#" + codtarget).data("dadositem");
  var dadosatl = $("#" + codtarget).data("dadosdoitematual");
  var config = $("#" + codtarget).data("combo-confitem");
  var ttopcpreco = 0;

  var tamanhoitem = null;
  var obssnoitem = null;
  var codsessao = null;
  var observacoes_dasessao = null;
  if (config == false && dadositemmontagem.item_observacoes == undefined) {
    tamanhoitem = dadosatl.data_tamanho;
    obssnoitem = false;
    codsessao = get_sessaoSabor(dadosatl.data_sabor[0]);
    observacoes_dasessao = get_observacoesdasessao(codsessao, tamanhoitem);
  } else {
    tamanhoitem = dadositemmontagem.item_tamanhoid;
    obssnoitem = dadositemmontagem.item_observacoes;
    codsessao = dadositemmontagem.item_sessaoid;
    observacoes_dasessao = get_observacoesdasessao(codsessao, tamanhoitem);
  }

  var htmlistaings = "";

  var cobrarobser = true;
  var opcionaisitem = config.opcionais;
  if (opcionaisitem != undefined) {
    cobrarobser =
      opcionaisitem.OBSERVASOES !== undefined &&
      opcionaisitem.OBSERVASOES.COBRAR == "S"
        ? true
        : false;
  }

  if (typeof itemSettings != "undefined" && itemSettings && itemSettings["OPCIONAIS"]["OBSERVASOES"]["COBRAR"] == "N") {
    cobrarobser = false;
  }

  if (observacoes_dasessao !== false) {
    show_listaObs(elemento);

    var cntobsss = observacoes_dasessao.length;
    for (var fd = 0; fd < cntobsss; fd++) {
      var codobs = observacoes_dasessao[fd].observacoes_id;
      var nomeobs = observacoes_dasessao[fd].observacoes_nome;
      var preco = observacoes_dasessao[fd].preco;
      preco =
        preco > 0 && cobrarobser === true ? " +R$ " + parseReal(preco) : "";
      var obsin = get_observacaoexist(obssnoitem, codobs);
      var ladobotao = !obsin ? "blbg_left" : "blbg_right";
      var bolabotao = !obsin ? "bl_left" : "bl_right";
      //var ladobotao = "blbg_left";
      //var bolabotao = "bl_left";

      htmlistaings +=
        "<li class='li_inglista ingrdts'><span class='nomeinglista'>" +
        nomeobs +
        preco +
        "</span>" +
        "<a href='#' class='obsitem_x bolabotao_link " +
        ladobotao +
        "' data-coditem='" +
        codobs +
        "' data-target-combo='" +
        codtarget +
        "' ><span class='bolabotao " +
        bolabotao +
        "'></span></a>" +
        "</li>";
    }

    $(".listacomobservacoesitem." + codtarget).html(htmlistaings);
    $(".topoobservacoes." + codtarget).text("Observações");
  } else {
    elemento.hide();
  }
  $(".nano").nanoScroller();
}

function rendListaBorda(elemento) {
  var codtarget = elemento.data("target-combo");
  var dadositemmontagem = $("#" + codtarget).data("dadositem");
  var dadosatl = $("#" + codtarget).data("dadosdoitematual");
  var config = $("#" + codtarget).data("combo-confitem");
  var ttopcpreco = 0;

  var tamanhoitem = null;
  var bordanoitem = null;
  var codsessao = null;
  var bordas_dasessao = null;
  if (config == false && dadositemmontagem.item_borda == undefined) {
    tamanhoitem = dadosatl.data_tamanho;
    bordanoitem = false;
    codsessao = get_sessaoSabor(dadosatl.data_sabor[0]);
    bordas_dasessao = get_bordadasessao(codsessao, tamanhoitem);
  } else {
    tamanhoitem = dadositemmontagem.item_tamanhoid;
    bordanoitem = dadositemmontagem.item_borda;
    codsessao = dadositemmontagem.item_sessaoid;
    bordas_dasessao = get_bordadasessao(codsessao, tamanhoitem);
  }

  var cobrarborda = true;
  var opcionaisitem = config.opcionais;
  if (opcionaisitem != undefined) {
    cobrarborda =
      opcionaisitem.BORDAS !== undefined && opcionaisitem.BORDAS.COBRAR == "S"
        ? true
        : false;
  }

  if (typeof itemSettings != "undefined" && itemSettings && itemSettings["OPCIONAIS"]["BORDAS"]["COBRAR"] == "N") {
    cobrarborda = false;
  }

  var htmlistaings = "";

  if (bordas_dasessao !== false) {
    let dados_sessao = get_dadosSessao(codsessao);
    let bordas = ordenaListaComplementos(dados_sessao.sessao_tipoordenacaocomplementos, bordas_dasessao);
    show_listaBorda(elemento);
    var ntipo = "";
    var cntobsss = bordas.length;
    for (var fd = 0; fd < cntobsss; fd++) {
      var codobs = bordas[fd].borda_id;
      var nomeobs = bordas[fd].borda_nome;
      var preco = bordas[fd].preco;
      preco =
        preco > 0 && cobrarborda === true ? " +R$ " + parseReal(preco) : "";

      var bordain = get_bordaexist(bordanoitem, codobs);
      var ladobotao = !bordain ? "blbg_left" : "blbg_right";
      var bolabotao = !bordain ? "bl_left" : "bl_right";

      var ds_nometipo = nomeobs.split(":");
      ntipo = ds_nometipo[0];

      htmlistaings +=
        "<li class='li_inglista ingrdts'><span class='nomeinglista'>" +
        nomeobs +
        preco +
        "</span>" +
        "<a href='#' class='bordaitem_x bolabotao_link " +
        ladobotao +
        "' data-coditem='" +
        codobs +
        "' data-target-combo='" +
        codtarget +
        "' ><span class='bolabotao " +
        bolabotao +
        "'></span></a>" +
        "</li>";
    }

    $(".listacombordasitem." + codtarget).html(htmlistaings);
    $(".topoborda." + codtarget).text(ntipo);
  } else {
    elemento.hide();
  }
  $(".nano").nanoScroller();
}

function rendListaComposicao(elemento) {
  let codtarget = elemento.data("target-combo");
  let catCompositionId = elemento.data('catcompositionid');
  let sizeId = elemento.data('codtam');
  item_tamanho = sizeId;
  let htmlCompositions = "";
  let htmlCompositionsAdd = "";
  
  let catComposition = getConfigCatCompositionByIdAndSize(catCompositionId, sizeId);
  let compositions = getCompositionsByCategorieAndSize(catCompositionId, sizeId);
  if (!compositions || !catComposition) {
    elemento.hide();
    $(".nano").nanoScroller();
    return;
  }

  let dados_sessao = get_dadosSessao(compositions[0]['COD_SESSAO']);
  compositions = ordenaListaComposicoes(dados_sessao.sessao_tipoordenacaocomposicoes, compositions);
  
  let catCompositionName = catComposition['NOME'];
  let catAvailability = catComposition['availability'];
  let catCalculation = catComposition['CALCULO_ITENS'];
  let catMaxAmountPerComposition = catComposition['maxAmountPerComposition'];
  let catMinAmount = catComposition['minAmount'];
  let catMaxAmount = catComposition['maxAmount'];
  let catMaxAmountAdd = parseInt(catComposition['maxAmountAdd']);
  let chargeAddCombo = true;
  let showAddCombo = true;

  if (configComposicoesItemCombo.hasOwnProperty(catCompositionId)) {
    if (configComposicoesItemCombo[catCompositionId]['COBRAR'] == 'N') {
      chargeAddCombo = false;
    }

    if (configComposicoesItemCombo[catCompositionId]['COBRAR'] == 'NP') {
      showAddCombo = false;
    }
  }

  if (typeof itemSettings != "undefined" && itemSettings && itemSettings["OPCIONAIS"]["COMPOSICOES"].hasOwnProperty(catCompositionId)) {
    if (itemSettings["OPCIONAIS"]["COMPOSICOES"][catCompositionId]['COBRAR'] == 'N') {
      chargeAddCombo = false;
    }
  
    if (itemSettings["OPCIONAIS"]["COMPOSICOES"][catCompositionId]['COBRAR'] == 'NP') {
      showAddCombo = false;
    }
  }

  show_listaComposicoes(elemento);
  for (let fd = 0; fd < compositions.length; fd++) {
    let composition = compositions[fd];
    let compositionId = composition['ID'];
    let price = catCalculation != 'NAO_COBRAR' ? composition['PRECO'] : 0;
    let compositionName = composition["NOME"];
    compositionName += (price > 0) && catCalculation != 'NAO_COBRAR' ? ` + R$ ${parseReal(price)}` : "";
    let compositionChecked = "";
    let compositionAmount = 0;
    let compositionCheckedAdd = "";
    let compositionAmountAdd = 0;

    if (compositionsItemMontador.compositions.length > 0) {
      let composition = compositionsItemMontador.compositions.filter(e => e['compositionId'] == compositionId);
      if (composition.length > 0) {
          let amountCompositionItem = parseInt(composition[0]['amount']);
          compositionAmount = amountCompositionItem;
          if (amountCompositionItem > 0) {
              compositionChecked = 'checked';
          }
      }
    }

    if (compositionsItemMontador.add.length > 0) {
      let composition = compositionsItemMontador.add.filter(e => e['compositionId'] == compositionId);
      if (composition.length > 0) {
          let amountCompositionItem = parseInt(composition[0]['amount']);
          compositionAmountAdd = amountCompositionItem;
          if (amountCompositionItem > 0) {
              compositionCheckedAdd = 'checked';
          }
      }
    }

    htmlCompositions += `
      <li class='li_inglista listCompositions ingrdts'>
        <label class='nomeinglista' for='list-compositionid-${compositionId}'>${compositionName}</label>
    `;

    if (catMaxAmount == 1) {
      htmlCompositions += `
          <label class='mdl-radio mdl-js-radio radio_composition' for='list-compositionid-${compositionId}'>
            <input type='radio' id='list-compositionid-${compositionId}' data-target-combo='${codtarget}' name='catcomposition${catComposition['ID']}' class='mdl-radio__button input_radio_composition' value='${compositionId}' data-price='${price}' data-catcompositionid='${catComposition['ID']}' ${compositionChecked}>
            <span class='mdl-radio__label'></span>
        </label>
      `;
    } else if (catMaxAmountPerComposition == 1) {
      htmlCompositions += `
          <div>
            <input type='checkbox' readonly='false' id='list-compositionid-${compositionId}' class='input_checkbox_composition' value='${compositionId}' data-price='${price}' data-catcompositionid='${catComposition['ID']}' ${compositionChecked}>
        </div>
      `;
    } else {
      htmlCompositions += 
        `<div class='btn_qtd_card'>
            <span class='qtd_menos qtd_menos_composicao' data-catcompositionid='${catComposition['ID']}' data-compositionId='${compositionId}' data-target-combo='${codtarget}'>-</span>
            <input class='qtd_txt inputComposition inteiro' data-catcompositionid='${catComposition['ID']}' data-price='${price}' data-compositionid='${compositionId}' value="${compositionAmount}" data-current-value='${compositionAmount}'>
            <span class='qtd_mais qtd_mais_composicao' data-compositionId='${compositionId}' data-catcompositionid='${catComposition['ID']}' data-target-combo='${codtarget}'>+</span>
        </div>`;
    }

    htmlCompositions += `
      </li>`;

    // configura os adicionais
    if (catCalculation == 'NAO_COBRAR' && composition['ADICIONAL'] == 'A' && catMaxAmountAdd > 0 && showAddCombo) {
      let nameCompositionAdd = composition["NOME"];
      composition['PRECO'] = chargeAddCombo ? composition['PRECO'] : 0;
      nameCompositionAdd += composition['PRECO'] > 0 ? ` + R$ ${parseReal(composition['PRECO'])}` : "";
      htmlCompositionsAdd += `
        <li class='li_inglista listCompositions ingrdts'>
          <label class='nomeinglista' for='add-list-compositionid-${compositionId}'>${nameCompositionAdd}</label>
      `;
      if (catMaxAmountAdd == 1) {
        htmlCompositionsAdd += `
            <label class='mdl-radio mdl-js-radio radio_composition' for='add-list-compositionid-${compositionId}'>
              <input type='radio' id='add-list-compositionid-${compositionId}' data-target-combo='${codtarget}' name='addCatcomposition${catComposition['ID']}' class='mdl-radio__button input_radio_compositionAdd' value='${compositionId}' data-price='${composition['PRECO']}' data-catcompositionid='${catComposition['ID']}' ${compositionCheckedAdd}>
              <span class='mdl-radio__label'></span>
          </label>
        `;
      } else {
        htmlCompositionsAdd += 
          `<div class='btn_qtd_card'>
              <span class='qtd_menos qtd_menos_composicaoAdd' data-compositionId='${compositionId}' data-catcompositionid='${catComposition['ID']}' data-target-combo='${codtarget}'>-</span>
              <input class='qtd_txt inputCompositionAdd inteiro' data-catcompositionid='${catComposition['ID']}' data-price='${composition['PRECO']}' data-compositionid='${compositionId}' value="${compositionAmountAdd}" data-current-value='${compositionAmountAdd}'>
              <span class='qtd_mais qtd_mais_composicaoAdd' data-compositionId='${compositionId}' data-catcompositionid='${catComposition['ID']}' data-target-combo='${codtarget}'>+</span>
          </div>`;
      }
      htmlCompositionsAdd += `  
        </li>`;
    }

  }

  if (htmlCompositionsAdd.length > 1) {
    let textOptionsAdd = catMaxAmountAdd > 1 ? 'opções adicionais' : 'opção adicional';
    htmlCompositionsAdd = `
      <ul class="ulCompositionAdd ${codtarget}">
        <li class="tituloopc">${catCompositionName} - Adicional<br>Selecione até ${catMaxAmountAdd} ${textOptionsAdd}</li>
        ${htmlCompositionsAdd} 
      </ul>`;
  }
  
  $(`.ulCompositionAdd.${codtarget}`).remove();
  $(".listacomcomposicoesitem." + codtarget).parent().append(htmlCompositionsAdd);
  $(".listacomcomposicoesitem." + codtarget).html(htmlCompositions);

  let textAvailability = catAvailability == 'OBRIGATORIO' ? 'Obrigatório' : 'Opcional';
  let textOptions = catMaxAmount > 1 ? 'opções' : 'opção';
  let textAmount = `Selecione até ${catMaxAmount} ${textOptions} (${textAvailability})`;
  textAmount = catAvailability == 'OBRIGATORIO' ? `Selecione ${catMaxAmount} ${textOptions} (${textAvailability})` : textAmount;
  if (catAvailability == 'OBRIGATORIO' && catMaxAmount > catMinAmount && catMaxAmount > 1) {
      textAmount = `Selecione de ${catMinAmount} à ${catMaxAmount} opções (${textAvailability})`;
  }

  $(".topocomposicoes." + codtarget).html(`<span>${catCompositionName}</span><span class='textAmountComposition'>${textAmount}</span>`);
}

function rendListaMassa(elemento, padrao) {
  var codtarget = elemento.data("target-combo");
  var dadositemmontagem = $("#" + codtarget).data("dadositem");
  var dadosatl = $("#" + codtarget).data("dadosdoitematual");
  var config = $("#" + codtarget).data("combo-confitem");
  var ttopcpreco = 0;

  var tamanhoitem = null;
  var massanoitem = null;
  var codsessao = null;
  var massa_dasessao = null;
  if (config == false && dadositemmontagem.item_massa == undefined) {
    tamanhoitem = dadosatl.data_tamanho;
    massanoitem = false;
    codsessao = get_sessaoSabor(dadosatl.data_sabor[0]);
    massa_dasessao = get_massasdasessao(codsessao, tamanhoitem);
  } else {
    tamanhoitem = dadositemmontagem.item_tamanhoid;
    massanoitem = dadositemmontagem.item_massa;
    codsessao = dadositemmontagem.item_sessaoid;
    massa_dasessao = get_massasdasessao(codsessao, tamanhoitem);
  }

  var cobrarmassa = true;
  var opcionaisitem = config.opcionais;
  if (opcionaisitem != undefined) {
    cobrarmassa =
      opcionaisitem.MASSA !== undefined && opcionaisitem.MASSA.COBRAR == "S"
        ? true
        : false;
  }

  var htmlistaings = "";

  if (massa_dasessao !== false) {
    let dados_sessao = get_dadosSessao(codsessao);
    let massas = ordenaListaComplementos(dados_sessao.sessao_tipoordenacaocomplementos, massa_dasessao);
    show_listaMassa(elemento);
    var ntipo = "";
    var cntobsss = massas.length;

    var massaselecteds = false;

    for (var fd = 0; fd < cntobsss; fd++) {
      var codobs = massas[fd].massa_id;
      var massain = get_massaexist(massanoitem, codobs);
      if (massain) {
        massaselecteds = true;
      }
    }

    for (var fd = 0; fd < cntobsss; fd++) {
      var codobs = massas[fd].massa_id;
      var nomeobs = massas[fd].massa_nome;
      var preco = massas[fd].preco;
      preco =
        preco > 0 && cobrarmassa === true ? " +R$ " + parseReal(preco) : "";
      var massain = get_massaexist(massanoitem, codobs);
      var ladobotao = !massain ? "blbg_left" : "blbg_right";
      var bolabotao = !massain ? "bl_left" : "bl_right";
      var ds_nometipo = nomeobs.split(":");
      ntipo = ds_nometipo[0];
      if (massaselecteds === false) {
        if (padrao == codobs) {
          ladobotao = "blbg_right";
          bolabotao = "bl_right";
        }
      }

      htmlistaings +=
        "<li class='li_inglista ingrdts'><span class='nomeinglista'>" +
        nomeobs +
        preco +
        "</span>" +
        "<a href='#' class='massaitem_x bolabotao_link " +
        ladobotao +
        "' data-coditem='" +
        codobs +
        "' data-target-combo='" +
        codtarget +
        "' ><span class='bolabotao " +
        bolabotao +
        "'></span></a>" +
        "</li>";
    }

    $(".listacommassasitem." + codtarget).html(htmlistaings);
    $(".topomassa." + codtarget).text(ntipo);
  } else {
    elemento.hide();
  }
  $(".nano").nanoScroller();
}
let finalizaItemAndamento = false;

$(document).ready(function () {
  $(document).on("keyup", ".buscarsabor", function () {
    var value = $(this).val();
    var prt = $(this).parent();
    prt = prt.parent();

    prt = prt.find(".itensdelistasabores");
    prt.each(function () {
      var txtelen_x = $(this).text();
      try {
        txtelen_x = txtelen_x.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      } catch (error_ueueb) {}

      if (txtelen_x.search(new RegExp(value, "i")) > -1) {
        $(this).show();
      } else {
        $(this).hide();
      }
    });
  });

  $(document).on("click", ".smaesertroca", function (e) {
    hide_listaSabores_comb();
  });
  $(document).on("click", ".close_sidemenu_sabortroca", function (e) {
    hide_listaSabores_comb();
  });
  $(document).on("click", ".clicktrocardeitem", function (e) {
    var daddos = $(this).data("dadostroca");
    trocarItem(daddos);
  });

  $("#montDorCombo").on("hidden.bs.modal", function () {
    $("#content_combo").html("");
  });

  $(document).on("click", "#btn-recomecar", function (e) {
    var dados = $("#cont_mont_lanche").data("dadositem");
    var tipo = dados.item_sessaoid;
    get_pizzaZerada(tipo);
  });

  $(document).on("change", ".selecttamitem", async function (e) {
    var codtamanho = $(this).val();
    var tamanhos = $(this).data("tamanhos");
    var codtarget = $(this).data("target-combo");
    rendQuantidadeSabores(codtamanho, tamanhos, codtarget);

    var elen = $(this);
    var dadosAcao = {
      tamanho: codtamanho,
    };

    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");

    var acao = "alterar";
    await atualizarTamanho(dadositemmontando, dadosAcao, acao, elen);
    $(".selectqtditem." + codtarget).change();
  });

  $(document).on("click", ".close_sidemenu", function (e) {
    $(".esmaecer_montador").trigger("click");
  });

  $(document).on("click", ".btnobs_montmodal", function (e) {
    rendListaObs($(this));
  });

  $(document).on("click", ".btnmss_montmodal", function (e) {
    var fgd = $(this).data("codmsspdr");
    rendListaMassa($(this), fgd);
  });

  $(document).on("click", ".btncomposicao_montmodal", function (e) {
    rendListaComposicao($(this));
  });

  //rendListaBorda(elemento)
  $(document).on("click", ".btnbrd_montmodal", function (e) {
    rendListaBorda($(this));
  });

  $(document).on("click", ".addunicoitem", function (e, triggered) {
    set_itemSimples($(this), "troca", triggered);
  });

  $(document).on("click", ".trocarmeuitem", function (e) {
    var allconf = $(this).parent().data("allconf");
    rendItensTroca(allconf);
  });

  $(document).on("click", ".addmenositem", function (e) {
    set_itemSimples($(this), "remove");
  });

  $(document).on("click", ".addmaisitem", function (e, triggered) {
    set_itemSimples($(this), "adiciona", triggered);
  });

  $(document).on("click", ".btnopc_montmodal", function (e) {
    show_listaIngredientes($(this));
    reendListaIngredientes($(this));
  });

  $(document).on("change", ".selectqtditem", function (e) {
    var qtdnova = $(this).val();
    var codtarget = $(this).data("target-combo");

    var elen = $(this);
    var dadosAcao = {
      qtdsabor: qtdnova,
    };

    //var dadositemmontando = $("#cont_modalmont").data("dadosdoitematual");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");

    var acao = "alterar";

    atualizarQtdSabor(dadositemmontando, dadosAcao, acao, elen);
  });

  $(document).on("click", ".itensdelistasabores", function () {
    if (!$(this).hasClass("clicktrocardeitem")) {
      hide_listaSabores($(this));
      if ($(this).hasClass("addsabor")) {
        set_saboritem($(this));
      } else {
        set_itemmontador($(this));
      }
    }
  });

  $(document).on("click", ".btnfinaliza_combo", async function () {
    if ($(this).hasClass("ativo")) {
      await finalizaCombo();
    } else {
      Swal({
        type: "info",
        title: "Oops..",
        text: "Selecione todos os itens do combo para finalizar",
      });
    }
  });

  $(document).on("click", ".openlistasabores", function (e) {
    abrirListaSabores($(this));
  });

  $(document).on("click", ".selectnovosabor", function (e) {
    abrirListaSabores($(this));
  });

  $(document).on("click", ".esmaecer_montador", function (e) {
    hide_listaSabores($(this));
    hide_listaIngredientes($(this));
  });

  $(document).on("click", ".abacombo", async function () {
    var target_aba = $(this).data("combo-abatarget");
    let targetItemValidation = $(".abacombo.ativa").data("combo-abatarget");
    let dados = $("#" + targetItemValidation).data("dadosdoitematual");

    if (dados && (dados.length > 0 || typeof dados == 'object')) {
      const setCompositions = await setCompositionsItemCombo(dados.data_hash, targetItemValidation, true);
      if (!setCompositions) return;
    }

    let configCombo = $("#" + target_aba).data("combo-confitem");
    if (configCombo) {
      configComposicoesItemCombo = configCombo.opcionais.hasOwnProperty('COMPOSICOES') ? configCombo.opcionais['COMPOSICOES'] : {};
    }

    item_tamanho = false;
    dados = $("#" + target_aba).data("dadositem");
    if (dados && (dados.length > 0 || typeof dados == 'object')) {
      compositionsItemMontador.compositions = dados.hasOwnProperty('item_compositions') ? dados.item_compositions : [];
      compositionsItemMontador.add = dados.hasOwnProperty('item_compositionsAdd') ? dados.item_compositionsAdd : [];
      item_tamanho = dados.hasOwnProperty('item_tamanhoid') ? dados.item_tamanhoid : false;
    }

    $(".abacombo").removeClass("ativa");
    $(this).addClass("ativa");
    $(".cont_abascombo").removeClass("abacontent_ativo");
    $("#" + target_aba).addClass("abacontent_ativo");

    var idnext = $(this).next();
    var idback = $(this).prev();
    idnext = idnext.data("combo-abatarget");
    idback = idback.data("combo-abatarget");

    if (idback == undefined) {
      $(".btnVoltar_combo").hide();
    } else {
      $(".btnVoltar_combo").show();
      $(".btnVoltar_combo").data("combo-abatarget", idback);
    }

    if (idnext == undefined) {
      $(".btnAvancar_combo").hide();
    } else {
      $(".btnAvancar_combo").show();
      $(".btnAvancar_combo").data("combo-abatarget", idnext);
    }

    $(".nano").nanoScroller();
  });

  $(document).on("click", ".btnAvancar_combo", function () {
    var target_aba = $(this).data("combo-abatarget");
    $(".abacombo[data-combo-abatarget='" + target_aba + "']").trigger("click");
  });
  $(document).on("click", ".btnVoltar_combo", function () {
    var target_aba = $(this).data("combo-abatarget");
    $(".abacombo[data-combo-abatarget='" + target_aba + "']").trigger("click");
  });

  $(document).on("click", ".bolabotao_link.bordaitem_x", function (e) {
    var elen = $(this);
    var codtarget = elen.data("target-combo");
    var codborda = elen.data("coditem");
    var dadosAcao = {
      codborda: codborda,
    };

    var rr = $(this).hasClass("blbg_left") ? true : false;
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    if (rr) {
      var acao = "adicionar";
      acoesBorda(dadositemmontando, dadosAcao, acao, elen);
      $(this).removeClass("blbg_left");
      $(this).addClass("blbg_right");
      $(this).children(".bolabotao").removeClass("bl_left");
      $(this).children(".bolabotao").addClass("bl_right");
    } else {
      var acao = "remover";
      acoesBorda(dadositemmontando, dadosAcao, acao, elen);
      $(this).removeClass("blbg_right");
      $(this).addClass("blbg_left");
      $(this).children(".bolabotao").removeClass("bl_right");
      $(this).children(".bolabotao").addClass("bl_left");
    }
  });

  $(document).on("click", ".bolabotao_link.massaitem_x", function (e) {
    var elen = $(this);
    var codtarget = elen.data("target-combo");
    var codmassa = elen.data("coditem");
    var dadosAcao = {
      codmassa: codmassa,
    };

    var rr = $(this).hasClass("blbg_left") ? true : false;
    //var dadositemmontando = $("#cont_modalmont").data("dadosdoitematual");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    if (rr) {
      var acao = "adicionar";
      acoesMassa(dadositemmontando, dadosAcao, acao, elen);
      $(this).removeClass("blbg_left");
      $(this).addClass("blbg_right");
      $(this).children(".bolabotao").removeClass("bl_left");
      $(this).children(".bolabotao").addClass("bl_right");
    }
  });

  $(document).on("click", ".bolabotao_link.obsitem_x", function (e) {
    var elen = $(this);
    var codtarget = elen.data("target-combo");

    var codobs = elen.data("coditem");
    var dadosAcao = {
      codobs: codobs,
    };

    var rr = $(this).hasClass("blbg_left") ? true : false;
    //var dadositemmontando = $("#cont_modalmont").data("dadosdoitematual");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    if (rr) {
      var acao = "adicionar";
      acoesObservacoes(dadositemmontando, dadosAcao, acao, elen);
      $(this).removeClass("blbg_left");
      $(this).addClass("blbg_right");
      $(this).children(".bolabotao").removeClass("bl_left");
      $(this).children(".bolabotao").addClass("bl_right");
    } else {
      var acao = "remover";
      acoesObservacoes(dadositemmontando, dadosAcao, acao, elen);
      $(this).removeClass("blbg_right");
      $(this).addClass("blbg_left");
      $(this).children(".bolabotao").removeClass("bl_right");
      $(this).children(".bolabotao").addClass("bl_left");
    }
  });

  $(document).on("click", ".bolabotao_link.ingopcsabores", function (e) {
    const elen = $(this);
    const rr = $(this).hasClass("blbg_left") ? true : false;
    const codtarget = elen.data("target-combo");
    const infTamanhoSelecionado = $(`#${codtarget}`).data('dadosdoitematual'); 
    let qtd_max_ingred_adic = infTamanhoSelecionado.qtd_max_ingred_adicionais; 
    if (qtd_max_ingred_adic === null || qtd_max_ingred_adic === undefined) {
      qtd_max_ingred_adic = $(`#${codtarget}`).data('qtd_max_ingred_adic') ? $(`#${codtarget}`).data('qtd_max_ingred_adic') : 1;
    }
    const ingred_adicionados = $(`ul.listacomingredientessabor_opc.${codtarget}`).find('.blbg_right');
    if (qtd_max_ingred_adic > 0
      && rr == true
      && ingred_adicionados.length >= qtd_max_ingred_adic
    ) {
      const Toast = Swal.mixin({
          //toast: true,
          //position: 'bottom-end',
          //showConfirmButton: false,
          timer: 4000,
          timerProgressBar: true,
          didOpen: (toast) => {
              toast.addEventListener('mouseenter', Swal.stopTimer)
              toast.addEventListener('mouseleave', Swal.resumeTimer)
          }
      });
      Toast.fire({
          type: 'error',
          title: `Não é possível adicionar mais que ${qtd_max_ingred_adic} ingredientes para este tamanho!`,
      })
      return false;
    }
    const codinsumo = elen.data("coding");
    const codsabor = elen.data("sabor");
    const pedaco = elen.data("pedaco");
    const dadosAcao = {
      insumo: codinsumo,
      sabor: codsabor,
      pedaco: pedaco,
    };


    //var dadositemmontando = $("#cont_modalmont").data("dadosdoitematual");
    const dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    if (rr) {
      acoesInsumos(dadositemmontando, dadosAcao, "adicionar", elen);
      $(this).removeClass("blbg_left");
      $(this).addClass("blbg_right");
      $(this).children(".bolabotao").removeClass("bl_left");
      $(this).children(".bolabotao").addClass("bl_right");
    } else {
      acoesInsumos(dadositemmontando, dadosAcao, "excluir", elen);
      $(this).removeClass("blbg_right");
      $(this).addClass("blbg_left");
      $(this).children(".bolabotao").removeClass("bl_right");
      $(this).children(".bolabotao").addClass("bl_left");
    }
  });

  $(document).on('click', '.qtd_mais_ing_add', function(e){
    let cod_ing = $(this).data('id_ing');
    let codtarget = $(this).data("target-combo");
    let dadositemmontando = $(`#${codtarget}`).data("dadosdoitematual");
    var codsabor = $(this).data("sabor");
    var pedaco = $(this).data("pedaco");
    let element_qtd = $(`.qtd_txt[data-id_ing="${cod_ing}"]`);
    let qtd_atual = element_qtd.html();
    let qtd_max = $(this).data('qtd_max');
    qtd_atual = parseInt(qtd_atual);
    qtd_max = parseInt(qtd_max);

    const infTamanhoSelecionado = $(`#${codtarget}`).data('dadosdoitematual'); 
    let qtd_max_ingred_adic = infTamanhoSelecionado.qtd_max_ingred_adicionais; ; 
    if (qtd_max_ingred_adic === null || qtd_max_ingred_adic === undefined) {
      qtd_max_ingred_adic = $(`#${codtarget}`).data('qtd_max_ingred_adic') ? $(`#${codtarget}`).data('qtd_max_ingred_adic') : 1;
    }

    let total_ingred_add = 0;

    $(`.qtd_txt[data-target-combo="${codtarget}"]`).each(function(e){
      let qtd = $(this).html();
      qtd = parseInt(qtd);
      total_ingred_add = total_ingred_add + qtd;
    });

    if(qtd_max_ingred_adic > 0 && total_ingred_add >= qtd_max_ingred_adic) {
      Swal({
        type: "warning",
        title: "Quantidade Inválida",
        html: `Não é possível adicionar mais que ${qtd_max_ingred_adic} ingredientes para este tamanho!`
      }); 
      return;
    }

    if(qtd_max > 0 && qtd_atual >= qtd_max) {
      Swal({
        type: "warning",
        title: "Quantidade Inválida",
        html: `Não é possível adicionar mais que ${qtd_max} de cada ingrediente!`
      }); 
      return;
    }
    let qtd_nova = parseInt(qtd_atual) + 1;
    element_qtd.html(qtd_nova);
    let acao = 'add_qtd_ing';

    let dadosAcao = {
      insumo: cod_ing,
      sabor: codsabor,
      pedaco: pedaco,
    };
    acoesInsumos(dadositemmontando, dadosAcao, acao, $(this), qtd_nova);
  });

  $(document).on('click', '.qtd_menos_ing_add', function(e){
    let cod_ing = $(this).data('id_ing');
    let codtarget = $(this).data("target-combo");
    let dadositemmontando = $(`#${codtarget}`).data("dadosdoitematual");
    var codsabor = $(this).data("sabor");
    var pedaco = $(this).data("pedaco");
    let element_qtd = $(`.qtd_txt[data-id_ing="${cod_ing}"]`);
    let qtd_atual = element_qtd.html();
    qtd_atual = parseInt(qtd_atual);
    if(qtd_atual <= 0) return;
    let qtd_nova = qtd_atual - 1;
    element_qtd.html(qtd_nova);
    let acao = 'remove_qtd_ing';

    let dadosAcao = {
      insumo: cod_ing,
      sabor: codsabor,
      pedaco: pedaco,
    };
    acoesInsumos(dadositemmontando, dadosAcao, acao, $(this), qtd_nova);
  });

  $(document).on("click", ".bolabotao_link.ingdossabores", function (e) {
    var elen = $(this);
    var codtarget = elen.data("target-combo");
    var codinsumo = elen.data("coding");
    var codsabor = elen.data("sabor");
    var pedaco = elen.data("pedaco");
    var dadosAcao = {
      insumo: codinsumo,
      sabor: codsabor,
      pedaco: pedaco,
    };

    var rr = $(this).hasClass("blbg_left") ? true : false;

    //var dadositemmontando = $("#cont_modalmont").data("dadosdoitematual");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    if (rr) {
      var acao = "readicionar";
      acoesInsumos(dadositemmontando, dadosAcao, acao, elen);
      $(this).removeClass("blbg_left");
      $(this).addClass("blbg_right");
      $(this).children(".bolabotao").removeClass("bl_left");
      $(this).children(".bolabotao").addClass("bl_right");
    } else {
      var acao = "remover";
      acoesInsumos(dadositemmontando, dadosAcao, acao, elen);
      $(this).removeClass("blbg_right");
      $(this).addClass("blbg_left");
      $(this).children(".bolabotao").removeClass("bl_right");
      $(this).children(".bolabotao").addClass("bl_left");
    }
  });

  /*
   * Remove ou realoca determinado insumo
   */
  $(document).on("change", ".lst_ings input[type='checkbox']", function (e) {
    var elen = $(this);
    var codtarget = elen.data("target-combo");
    var codinsumo = elen.val();
    var codsabor = elen.data("sabor");
    var pedaco = elen.data("pedaco");
    var dadosAcao = {
      insumo: codinsumo,
      sabor: codsabor,
      pedaco: pedaco,
    };

    //var dadositemmontando = $("#cont_modalmont").data("dadosdoitematual");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    if ($(this).is(":checked")) {
      var acao = "readicionar";
      acoesInsumos(dadositemmontando, dadosAcao, acao, elen);
      $(this).parent().css("text-decoration", "none");
    } else {
      var acao = "remover";
      acoesInsumos(dadositemmontando, dadosAcao, acao, elen);
      $(this).parent().css("text-decoration", "line-through");
    }
  });

  $(document).on("change", ".lst_ings_opc input[type='checkbox']", function (
    e
  ) {
    var elen = $(this);
    var codtarget = elen.data("target-combo");
    var codinsumo = elen.val();
    var codsabor = elen.data("sabor");
    var pedaco = elen.data("pedaco");
    var dadosAcao = {
      insumo: codinsumo,
      sabor: codsabor,
      pedaco: pedaco,
    };

    //var dadositemmontando = $("#cont_modalmont").data("dadosdoitematual");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    if (!$(this).is(":checked")) {
      var acao = "excluir";
      acoesInsumos(dadositemmontando, dadosAcao, acao, elen);
      elen.parent().remove();
    }
  });

  $(document).on("click", ".maisum_item", function (e) {
    var elen = $(this);
    var codtarget = elen.data("target-combo");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    var acao = "adiciona";
    acoesAdicionaRemove(dadositemmontando, acao, codtarget);
  });

  $(document).on("click", ".menosum_item", function (e) {
    var elen = $(this);
    var codtarget = elen.data("target-combo");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    var acao = "remove";
    acoesAdicionaRemove(dadositemmontando, acao, codtarget);
  });
  //

  $(document).on("click", ".comprar_item", async function (e) {
    if (finalizaItemAndamento) {
      console.error('finalizaPedidoAndamento');
      return;
    }

    var elen = $(this);
    var codtarget = elen.data("target-combo");
    var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
    var detalhes = $("#cont_mont_lanche").data("dadosdoitematual");
    let obs = $('.obs_item').val();

    if(obs && obs.length > 0 && (obs.length < 3 || obs.length > 140)){
      Swal({
        type: "warning",
        title: "Observação Inválida",
        html: 'A observação deve ter entre 3 e 140 caracteres.'
      }); 
      return;
    }

    finalizaItemAndamento = true;

    dadositemmontando.data_obs = obs;
    configComposicoesItemCombo = {};
    const checkCompositions = await checkItemCompositions();
    if (!checkCompositions) {
      finalizaItemAndamento = false;
      return;
    }

    const checkCompositionsAdd = await checkItemCompositions('Add');
    if (!checkCompositionsAdd) {
      finalizaItemAndamento = false;
      return;
    }

    dadositemmontando.compositions = await getCompositionsItem();
    dadositemmontando.compositionsAdd = await getCompositionsItem('Add');

    const upsellItemsAdd = await getUpsellItemsProduct('.upsell_montador_padrao_desktop');
    if (upsellItemsAdd) dadositemmontando.upsell = upsellItemsAdd;
    finaliza_itemComprar(dadositemmontando, codtarget, detalhes);
  });
});

function finaliza_itemComprar(dadositemmontando, codtarget, detalhes) {
  var dados = {
    dadositem: dadositemmontando,
  };

  Cookies.set('itemInEditingED', dadositemmontando["data_hash"]);
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/finalizaitem/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    Cookies.remove("itemInEditingED");
    finalizaItemAndamento = false;
    finalizaPizzaAndamento = false;
    hideLoading();
    if (msg.res === true) {
      if ((fbp_configurado == true || tiktokpixel_configurado == true) && detalhes != undefined) {
        if (detalhes.sabores != undefined && detalhes.sabores != null) {
          var nome_item = "";
          var sabores = detalhes.sabores;

          sabores.forEach(function (sabor) {
            if (sabor != null) {
              if (sabor.item_sabornome != null) {
                if (nome_item == "") {
                  nome_item = sabor.item_sabornome;
                } else {
                  nome_item = nome_item + " / " + sabor.item_sabornome;
                }
              }
            }
          });

          if (fbp_configurado == true) {
            fbq("track", "AddToCart", {
                content_name: nome_item,
                content_category: detalhes.item_tamanhonome,
                content_ids: [detalhes.item_cod],
                content_type: "product",
                value: detalhes.item_preco,
                currency: "BRL",
              },
              {
                eventID: facebookEventID
              }
            );
          }

          if (tiktokpixel_configurado == true) {
            ttq.track('AddToCart', {
              content_name: nome_item,
              content_category: detalhes.item_tamanhonome,
              content_id: [detalhes.item_cod],
              content_type: "product",
              value: detalhes.item_preco,
              currency: "BRL",
            });
          }

          if (dadositemmontando.upsell && dadositemmontando.upsell.length > 0) {
            for (let i = 0; i < dadositemmontando.upsell.length; i++) {
              const itemUpsell = dadositemmontando.upsell[i];
              if (fbp_configurado == true) {
                fbq('track', 'AddToCart', {
                    content_name: itemUpsell.itemName, 
                    content_category: itemUpsell.sessionName,
                    content_ids: [itemUpsell.itemId],
                    content_type: 'product',
                    value: itemUpsell.price,
                    currency: 'BRL'
                  },
                  {
                    eventID: facebookEventID
                  }
                );
              }
              
              if (tiktokpixel_configurado == true) {
                ttq.track('AddToCart', {
                  content_name: itemUpsell.itemName, 
                  value: itemUpsell.price,
                  content_category: itemUpsell.sessionName,
                  content_id: [itemUpsell.itemId],
                  content_type: 'product',
                  currency: 'BRL'
                });
              }

              if (GA4_configurado) {
                gtag("event", "add_to_cart", {
                  currency: "BRL",
                  value: itemUpsell.price,
                  items: [
                    {
                      item_id: itemUpsell.itemId,
                      item_name: itemUpsell.itemName,
                      item_category: itemUpsell.sessionName,
                      price: itemUpsell.price,
                      quantity: itemUpsell.amount
                    }
                  ]
                });
              }
            }
          }
        }
      }

      $("#montDor").modal("hide");

      if (window.location.href.indexOf("programa-fidelidade") > -1) {
        window.location.reload();
      }

      showModalpromocao = true;
      if (mtpzz === true) {
        var montadoratualpagina = "S";
        if (msg.mpagina != undefined) {
          montadoratualpagina = msg.mpagina;
        }
        if (montadoratualpagina == "S") {
          get_pizzaZerada(msg.dados.tipocod);
          Ancora("formapizza");
        }
      }
      showMsgItemAdd();
      get_resumoPedido();
      resetArrayCompositionsItem();
    } else if (msg.res === false) {
      if (msg.msg != undefined) {
        if (msg.msgTitle) {
          Swal({
              type: 'warning',
              title: msg.msgTitle,
              html: msg.msg
          });
          return;
        }
        if(msg.delivery_fechado && msg.delivery_fechado == true){
          Swal({
            type: 'info',
            title: 'Delivery Online - FECHADO',
            html: `Você poderá navegar normalmente, mas não poderá adicionar itens ao pedido.<br>${htmlServiceHoursToday}`,
          });
          return;
        }
        if(msg.erro_tamanhosabores && msg.erro_tamanhosabores == true){
          Swal({
            type: 'warning',
            title: 'Erro ao Finalizar Item',
            html: msg.msg,
          });
          return;
        }
        Swal({
          type: "info",
          title: msg.msg,
          text: "Essa opção é obrigatória",
          onClose: () => {
            if ($('#montDor').is(':visible')) {
              $(".btnbrd_montmodal").trigger("click");
            } else {
              $(".openmodalborda").trigger("click");
            }
          },
        }); 
        return;
      }

      if(msg.erro_msg != undefined){
        Swal({
          type: "error",
          title: "Oops..",
          html: msg.erro_msg,
          onClose: () => {
            document.location.reload();
          }
        }); 
        return;
      }      
    }
  });
}

function get_pizzaZerada(cod) {
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/zerarpizza/",
    data: { tipo: cod },
    dataType: "json",
  }).done(function (msg) {
    if (msg.res === true) {
      $("#itemSettings").val("null");
      itemSettings = null;
      Cookies.remove("itemInEditingED");
      peencheDadosRetorno(msg);
      rendPizzaFormaPizza(msg.item);
      redir_item = true;
      limpa_box_ingredientes();
      resetAmountUpsell();
      $('.obs_item').val('');
    } else if (msg.res === false) {
    } else {
    }
  });
}

/*
var massa = get_massa_dados(confiditem.massa);
var tamanho = get_tamanho_dados(confiditem.tamanho);
*/
function get_nomes_sabores(lista, tamanho) {
  var cnt = lista.length;
  var cnt_sabores = sabores_itens.length;
  var lst = [];
  var cntin = 0;

  for (var t = 0; t < cnt_sabores; t++) {
    var idsabor = sabores_itens[t].sabor_id;
    for (var i = 0; i < cnt; i++) {
      var codsabor = lista[i];
      if (idsabor == codsabor) {
        if (sabores_itens[t].sabor_precostamanhos != undefined) {
          var cnty = sabores_itens[t].sabor_precostamanhos.length;
          for (var c = 0; c < cnty; c++) {
            if (
              sabores_itens[t].sabor_precostamanhos[c]
                .sabor_precotamanhos_codtamanho == tamanho
            ) {
              lst[cntin] = sabores_itens[t];
              cntin++;
            }
          }
        } else {
          lst[cntin] = sabores_itens[t];
          cntin++;
        }
      }
    }
  }
  return lst;
}

function get_borda_dados(borda, tamanho) {
  var cnt = bordas_itens.length;
  for (var i = 0; i < cnt; i++) {
    if (bordas_itens[i].borda_id == borda) {
      var cntt = bordas_itens[i].borda_precotamanho.length;
      for (var y = 0; y < cntt; y++) {
        if (
          bordas_itens[i].borda_precotamanho[y].precotamannho_tamanhoid ==
          tamanho
        ) {
          bordas_itens[i]["borda_preco"] =
            bordas_itens[i].borda_precotamanho[y].precotamannho_preco;
          return bordas_itens[i];
        }
      }
    }
  }
  return false;
}
function get_massa_dados(massa, tamanho) {
  var cnt = massas_itens.length;
  for (var i = 0; i < cnt; i++) {
    if (massas_itens[i].massa_id == massa) {
      var cntt = massas_itens[i].massa_precotamanho.length;
      for (var y = 0; y < cntt; y++) {
        if (
          massas_itens[i].massa_precotamanho[y].precotamannho_tamanhoid ==
          tamanho
        ) {
          massas_itens[i]["massa_preco"] =
            massas_itens[i].massa_precotamanho[y].precotamannho_preco;
          return massas_itens[i];
        }
      }
    }
  }
  return false;
}
function get_tamanho_dados(tamanho) {
  var cnt = tamahos_itens.length;
  for (var i = 0; i < cnt; i++) {
    if (tamahos_itens[i].tamanho_id == tamanho) {
      return tamahos_itens[i];
    }
  }
  return false;
}

function reendListaIngredientes(elemento) {
  var codtarget = elemento.data("target-combo");
  var codsabor = elemento.data("codsabor");
  var pedaco = elemento.data("pdc");
  var dadositematual = $("#" + codtarget).data("dadosdoitematual");
  var dadositemmontagem = $("#" + codtarget).data("dadositem");
  var tamanhoitem = dadositematual.data_tamanho;
  var qtdsabor = dadositemmontagem.item_qtdsabor;
  var config = $("#" + codtarget).data("combo-confitem");
  var ttopcpreco = 0;
  let qtd_max_por_ingred_adicionais = dadositemmontagem.hasOwnProperty('item_qtd_max_por_ingred_adicionais') && dadositemmontagem.item_qtd_max_por_ingred_adicionais > -1 ? dadositemmontagem.item_qtd_max_por_ingred_adicionais : 1; 
  if(qtd_max_por_ingred_adicionais === 1){
    qtd_max_por_ingred_adicionais = dadositematual.hasOwnProperty('qtd_max_por_ingred_adicionais') && dadositematual.qtd_max_por_ingred_adicionais > -1 ? dadositematual.qtd_max_por_ingred_adicionais : 1;
  }
 
  var htmlistaings = "";
  var htmllistingsopc = "";
  //listadeingredientes_opc
  var dadossabor = get_dadossabor(codsabor);
  
  let permite_addingredientes = dadossabor.sabor_sessao_addingrediente ? dadossabor.sabor_sessao_addingrediente : 'N';

  if (dadossabor !== false) {
    var nomesabor = dadossabor.sabor_nome;
    var categoriasabor = dadossabor.sabor_categorianome;
    var codsessaosabor = dadossabor.sabor_sessaoid;
    var ings_sabor = dadossabor.sabor_ingredientes;
    if (ings_sabor !== undefined && ings_sabor.length > 0) {
      var cntingsab = ings_sabor.length;
      for (var ig = 0; ig < cntingsab; ig++) {
        var coging = ings_sabor[ig].sabor_ingrediente_codingrediente;

        var ingrem = ingred_rem(
          dadositemmontagem.sabores,
          pedaco,
          ings_sabor[ig].sabor_ingrediente_codingrediente
        );

        var ladobotao = ingrem ? "blbg_left" : "blbg_right";
        var bolabotao = ingrem ? "bl_left" : "bl_right";

        htmlistaings +=
          "<li class='li_inglista ingrdts'><span class='nomeinglista'>" +
          ings_sabor[ig].sabor_ingrediente_nomeingrediente +
          "</span>";
        if(dadossabor.sabor_sessao_removeingrediente && dadossabor.sabor_sessao_removeingrediente == 'S'){
          htmlistaings += "<a href='#' class='ingdossabores bolabotao_link " +
            ladobotao +
            "' data-coding='" +
            coging +
            "' data-target-combo='" +
            codtarget +
            "' data-sabor='" +
            codsabor +
            "' data-pedaco='" +
            pedaco +
            "' ><span class='bolabotao " +
            bolabotao +
            "'></span></a>";
        }
        htmlistaings += "</li>";
      }
    }
    $(".titulo_nomesabor." + codtarget).text(nomesabor);

    let chargeIngredient = true;
    let showIngredients = true;
    if (typeof itemSettings != "undefined" && itemSettings) {
      if (itemSettings["OPCIONAIS"]["INGREDIENTE"]["COBRAR"] == "N") {
        chargeIngredient = false;
      }

      if (itemSettings["OPCIONAIS"]["INGREDIENTE"]["COBRAR"] == "NP") {
        showIngredients = false;
      }
    }

    if (showIngredients && (config == false || config.opcionais.INGREDIENTE.COBRAR !== "NP")) {
      if (dadossabor.sabor_ingredientesopcionais !== undefined) {
        var contingopc = dadossabor.sabor_ingredientesopcionais.length;
        for (var iopc = 0; iopc < contingopc; iopc++) {
          htmllistingsopc += "";
        }
      } else {
        var confings = ingredientes_itens.length;
        for (var hj = 0; hj < confings; hj++) {
          if (
            ingredientes_itens[hj].ingrediente_opcional === "S" &&
            codsessaosabor == ingredientes_itens[hj].ingrediente_sessaoid
          ) {
            if (ingredientes_itens[hj].ingredientes_precotamanho !== undefined && permite_addingredientes == 'S') {
              var precoingopc = get_precoIngrediente(
                ingredientes_itens[hj],
                tamanhoitem,
                config,
                qtdsabor
              );

              if (!chargeIngredient) precoingopc = 0;

              if (precoingopc !== false) {
                var coging = ingredientes_itens[hj].ingrediente_id;
                var nomeingopc = ingredientes_itens[hj].ingrediente_nome;
                var ingopcenfalta = ingredientes_itens[hj].ingrediente_emfalta;
                var ingadd = ingred_add(
                  dadositemmontagem.sabores,
                  pedaco,
                  coging
                );

                ttopcpreco = ingadd ? ttopcpreco + precoingopc : ttopcpreco;

                var ladobotao = ingadd ? "blbg_right" : "blbg_left";
                var bolabotao = ingadd ? "bl_right" : "bl_left";

                precoingopc =
                  precoingopc > 0
                    ? "<span class='ingopcpreco'> + " +
                      parseReal(precoingopc) +
                      "</span>"
                    : "";
                htmllistingsopc +=
                  "<li class='li_inglista'><span class='nomeinglista'>" +
                  nomeingopc +
                  precoingopc +
                  "</span>";

                  if(qtd_max_por_ingred_adicionais == 1) {
                    htmllistingsopc += "<a href='#' class='ingopcsabores bolabotao_link " +
                      ladobotao +
                      "' data-coding='" +
                      coging +
                      "'  data-target-combo='" +
                      codtarget +
                      "' data-sabor='" +
                      codsabor +
                      "' data-pedaco='" +
                      pedaco +
                      "' ><span class='bolabotao " +
                      bolabotao +
                      "'></span></a>";
                  } else {
                    let qtd_ing_add = qtd_ingred_add(
                      dadositemmontagem.sabores,
                      pedaco,
                      coging
                    );
                    htmllistingsopc += 
                      `<div class='btn_qtd_card'>
                          <span class='qtd_menos qtd_menos_ing_add' data-id_ing='${coging}' data-target-combo='${codtarget}' data-sabor='${codsabor}' data-pedaco='${pedaco}'>-</span>
                          <span class='qtd_txt' data-target-combo='${codtarget}' data-id_ing='${coging}'>${qtd_ing_add}</span>
                          <span class='qtd_mais qtd_mais_ing_add' data-id_ing='${coging}' data-qtd_max='${qtd_max_por_ingred_adicionais}' data-target-combo='${codtarget}' data-sabor='${codsabor}' data-pedaco='${pedaco}'>+</span>
                      </div>`;
                  }
                  htmllistingsopc += "</li>";
              }
            }
          }
        }
      }
    }
  }

  var valopcpreco = ""; //(ttopcpreco>0)? " (+R$ "+ parseReal(ttopcpreco) +")" : "";
  htmllistingsopc =
    htmllistingsopc != ""
      ? "<li class='tituloopc'>Ingredientes Opcionais" +
        valopcpreco +
        "</li>" +
        htmllistingsopc
      : htmllistingsopc;

  $(".listacomingredientessabor." + codtarget).html(htmlistaings);
  $(".listacomingredientessabor_opc." + codtarget).html(htmllistingsopc);
  //$(".listadeingredientes_opc."+codtarget).stop().animate({right: '0px'}, 400);
  //sabor_ingredientesopcionais
  $(".nano").nanoScroller();

  /*
         ingrediente_categoria:"salgado"
         ingrediente_emfalta:"N"
         ingrediente_id:"46"
         ingrediente_nome:"Tomate Picado"
         ingrediente_opcional:"S"
         ingrediente_sessaoid:"5"
         ingredientes_precotamanho
         */
}

function ingred_rem(saboresit, pedaco, coding) {
  if (saboresit != undefined) {
    var cntsabor = saboresit.length;
    for (var i = 0; i < cntsabor; i++) {
      if (saboresit[i].item_saborpedaco == pedaco) {
        if (saboresit[i].item_saboringredrem !== false) {
          var cntingrem = saboresit[i].item_saboringredrem.length;
          for (var rs = 0; rs < cntingrem; rs++) {
            if (
              saboresit[i].item_saboringredrem[rs].ingrediente_cod == coding
            ) {
              return true;
            }
          }
        }
      }
    }
  }
  return false;
}

function ingred_add(saboresit, pedaco, coding) {
  if (saboresit != undefined) {
    var cntsabor = saboresit.length;
    for (var i = 0; i < cntsabor; i++) {
      if (saboresit[i].item_saborpedaco == pedaco) {
        if (saboresit[i].item_saboringredcom !== false) {
          var cntingrem = saboresit[i].item_saboringredcom.length;
          for (var rs = 0; rs < cntingrem; rs++) {
            if (
              saboresit[i].item_saboringredcom[rs].ingrediente_cod == coding
            ) {
              return true;
            }
          }
        }
      }
    }
  }
  return false;
}

function qtd_ingred_add(saboresit, pedaco, coding) {
  if (saboresit != undefined) {
    var cntsabor = saboresit.length;
    for (var i = 0; i < cntsabor; i++) {
      if (saboresit[i].item_saborpedaco == pedaco) {
        if (saboresit[i].item_saboringredcom !== false) {
          var cntingrem = saboresit[i].item_saboringredcom.length;
          for (var rs = 0; rs < cntingrem; rs++) {
            if (
              saboresit[i].item_saboringredcom[rs].ingrediente_cod == coding
            ) {
              return saboresit[i].item_saboringredcom[rs].ingrediente_qtd;
            }
          }
        }
      }
    }
  }
  return 0;
}

function get_dadossabor(codsabor) {
  if (sabores_itens !== undefined && sabores_itens.length > 0) {
    var contsabor = sabores_itens.length;
    for (var i = 0; i < contsabor; i++) {
      if (sabores_itens[i].sabor_id == codsabor) {
        return sabores_itens[i];
      }
    }
  }
  return false;
}

function set_itemSimples(elemento, acao, triggered, input = false) {
  var codtarget = elemento.data("target-combo");
  var infocombo = $("#montador_combo").data("combo-infos");
  var confitem = $("#" + codtarget).data("combo-confitem");
  var sabor = elemento.data("codsabor");
  var codtamanho = elemento.data("codtam");
  let qtd = input ? input.val() : 1;

  if(triggered == true){
    qtd = confitem.quantidade;
  }
   
  var dados = {
    data_codconfcombo: confitem.codconfig,
    data_codcombo: infocombo.combo_id,
    data_fid: infocombo.fidelidade,
    data_hascombo: $("#montador_combo").data("combo-hash"),
    data_hashitem: confitem.hash,
    data_itemtamanho: codtamanho,
    data_itemsabor: sabor,
    data_acao: acao,
    quantidade: qtd,
    cod_resgate: infocombo.cod_resgate
  };
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/setitemsimplescombo/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    hideLoading();
    if (msg.res === true) {
      var qtdatl = msg.dado.qtd;
      var comple = msg.dado.completo;
      if (input) input.val(qtdatl);
      combocompleto(msg.dado.combocompleto);
      if (acao === "adiciona" || acao === "remove" || acao === "alterar_x") {
        var parentinput = elemento.parent();
        var boxitem = parentinput.parent();
        parentinput.children(".valqtditem").val(qtdatl);
        if (qtdatl > 0) {
          boxitem.removeClass("zeroitem");
        } else {
          boxitem.addClass("zeroitem");
        }

        if (comple === true) {
          $(".item_simp_comb." + codtarget + ".zeroitem").addClass("inativo");
        } else {
          $(".item_simp_comb." + codtarget + ".zeroitem").removeClass(
            "inativo"
          );
        }
      } else if (acao === "troca") {
        $(".item_simp_comb." + codtarget).removeClass("selecionado");
        var boxitem = elemento.parent();
        boxitem.addClass("selecionado");
      }

      if (msg.dado.quantityLeft) {
        Swal({
          type: "warning",
          title: "Oops..",
          html: `Quantidade máxima excedida.<br>Selecione até ${msg.dado.quantityLeft} iten(s).`
        }); 
      }

      comboiniciado_ok = true;
    } else if (msg.res === false) {
      if (input) $(input).val(currentComboItemQuantity);

      if(msg.erro_msg != undefined){
        Swal({
            type: "error",
            title: "Oops..",
            html: msg.erro_msg,
            onClose: () => {
                document.location.reload();
            }
        }); 
    }  
    } else {
    }
  });
}

function acoesAdicionaRemove(dadositemmontando, acao, codtarget) {
  var dados = {
    dadositem: dadositemmontando,
    acao: acao,
  };

  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/maismenos_item/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    if (msg.res === true) {
      peencheDadosRetorno(msg, codtarget);
      peencheMontadorItem(codtarget);
    } else if (msg.res === false) {
      if(msg.erro_msg != undefined){
        Swal({
            type: "error",
            title: "Oops..",
            html: msg.erro_msg,
            onClose: () => {
                document.location.reload();
            }
        }); 
      }
    } else {
    }
  });
}

function set_saboritem(elemento) {
  var codtarget = elemento.data("target-combo");

  var dadositemmontando = $("#" + codtarget).data("dadosdoitematual");
  var pedaco = elemento.data("pdc");

  $(".esmaecer_montador." + codtarget).removeClass("noitemselected");
  setTimeout(function () {
    $(".esmaecer_montador." + codtarget).removeClass("blackesm");
  }, 400);

  var dadosAcao = {
    data_sabor: elemento.data("codsabor"),
    data_pedaco: pedaco,
  };

  var dados = {
    dadositem: dadositemmontando,
    dadosacao: dadosAcao,
    acao: "adicionar",
  };
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/sabores/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    hideLoading();
    if (msg.res === true) {
      peencheDadosRetorno(msg, codtarget);
      peencheMontadorItem(codtarget);
      comboiniciado_ok = true;
    } else if (msg.res === false) {
    } else {
    }
  });
}

function combocompleto(combocompleto) {
    
    if (combocompleto === true) {
        $("#btnfinalizacombo").animateCss("tada");
        $("#btnfinalizacombo").addClass("completou");
        if(!$(".btnfinaliza_combo").hasClass("ativo")){
            $(".btnfinaliza_combo").addClass("ativo");
        }
    }else if(combocompleto === false){
        if($("#btnfinalizacombo").hasClass("completou")){
            $(".btnfinaliza_combo").removeClass("ativo");
        }else if(!$(".btnfinaliza_combo").hasClass("ativo")){
            $(".btnfinaliza_combo").addClass("ativo");
        }
    }
}

function set_itemmontador(elemento) {
  var codtarget = elemento.data("target-combo");
  var infocombo = $("#montador_combo").data("combo-infos");
  var confitem = $("#" + codtarget).data("combo-confitem");
  var pedaco = elemento.data("pdc");

  $(".esmaecer_montador." + codtarget).removeClass("noitemselected");
  setTimeout(function () {
    $(".esmaecer_montador." + codtarget).removeClass("blackesm");
  }, 400);

  var dados = {
    data_codconfcombo: confitem.codconfig,
    data_codcombo: infocombo.combo_id,
    data_fid: infocombo.fidelidade,
    data_hascombo: $("#montador_combo").data("combo-hash"),
    data_hashitem: confitem.hash,
    data_itemtamanho: elemento.data("codtamanho"),
    data_itemsabor: elemento.data("codsabor"),
    data_pedaco: pedaco,
    cod_resgate: infocombo.cod_resgate
  };
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/setitemcombo/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    resetArrayCompositionsItem();
    hideLoading();
    if (msg.res === true) {
      msg.dados.hasitem;
      msg.dados.itemrend;

      var codsabor = [];
      if (
        msg.dados.itemrend.sabores !== undefined &&
        msg.dados.itemrend.sabores.length > 0
      ) {
        for (var ie = 0; ie < msg.dados.itemrend.sabores.length; ie++) {
          codsabor[ie] = msg.dados.itemrend.sabores[ie].item_saborid;
        }
      }
      var dadositem = {
        data_hash: msg.dados.hasitem,
        data_sabor: codsabor,
        data_tamanho: msg.dados.itemrend.item_tamanhoid,
        data_qtdsabor: msg.dados.itemrend.item_qtdsabor,
      };

      $("#" + codtarget).data("dadosdoitematual", dadositem);
      $("#" + codtarget).data("dadositem", msg.dados.itemrend);
      peencheMontadorItem(codtarget);

      combocompleto(msg.dados.combocompleto);
      comboiniciado_ok = true;
    } else if (msg.res === false) {
      if(msg.erro_msg != undefined){
        Swal({
            type: "error",
            title: "Oops..",
            html: msg.erro_msg,
            onClose: () => {
                document.location.reload();
            }
        }); 

      }  
      Swal({
        type: "error",
        title: "Oops..",
        html: msg.msg
      }); 
      $("#montDorCombo").modal("hide"); 
    }
  });
}

async function peencheDadosRetorno(msg, codtarget) {
  if (msg.item && msg.item["sabores"].length > 0) {
    let subtractValue = 0;
    for (const flavor of msg.item["sabores"]) {
      if (flavor["item_saboringredcom"]) {
        for (const ingredient of flavor["item_saboringredcom"]) {
          if (typeof itemSettings != "undefined" && itemSettings && itemSettings["OPCIONAIS"]["INGREDIENTE"]["COBRAR"] == "N") {
            subtractValue += parseFloat(ingredient["ingrediente_preco"]);
          }
        }
      }
    }
    msg.item.item_preco = parseFloat(msg.item.item_preco) - subtractValue;
    msg.item.ingredientsPriceUpdated = true;
  }
  
  if (codtarget != undefined && codtarget != false) {
    var dadositem = $("#" + codtarget).data("dadosdoitematual");
    var codsabor = [];
    if (msg.item != undefined) {
      if (msg.item.sabores !== undefined && msg.item.sabores.length > 0) {
        for (var ie = 0; ie < msg.item.sabores.length; ie++) {
          codsabor[ie] = msg.item.sabores[ie].item_saborid;
        }
      }
      if (msg.item.hash != undefined) {
        dadositem = {};
        dadositem["data_hash"] = msg.item.hash;
      }
      dadositem["data_sabor"] = codsabor;
      dadositem["data_tamanho"] = msg.item.item_tamanhoid;
      dadositem["data_qtdsabor"] = msg.item.item_qtdsabor;
      dadositem["data_bordas"] = msg.item.item_borda;
      dadositem["qtd_max_ingred_adicionais"] = msg.item.item_qtd_max_ingred_adicionais
      if(msg.item.item_obs) dadositem["data_obs"] = msg.item.item_obs;
      $("#" + codtarget).data("dadositem", msg.item);
    } else if (msg.dados.dadossabores != undefined) {
      dadositem = {};
      dadositem["data_sabor"] = msg.dados.dadossabores[0].sabor_id;
      dadositem["data_tamanho"] =
        msg.dados.dadossabores[0].sabor_precostamanhos[0].sabor_precotamanhos_codtamanho;
      dadositem["data_qtdsabor"] = 1;
    }
    dadositem['data_compositions'] = [];
    dadositem['data_compositionsAdd'] = [];
    if (msg.item_compositions) dadositem['data_compositions'] = msg.item_compositions; 
    if (msg.item_compositionsAdd) dadositem['data_compositionsAdd'] = msg.item_compositions; 
    $("#" + codtarget).data("dadosdoitematual", dadositem);
  } else {
    var dadositem = $("#cont_mont_lanche").data("dadosdoitematual");
    var codsabor = [];
    if (msg.item != undefined) {
      if (msg.item.sabores !== undefined && msg.item.sabores.length > 0) {
        for (var ie = 0; ie < msg.item.sabores.length; ie++) {
          codsabor[ie] = msg.item.sabores[ie].item_saborid;
        }
      }
      if (msg.item.hash != undefined) {
        dadositem = {};
        dadositem["data_hash"] = msg.item.hash;
      } else if (msg.item.item_hash != undefined) {
        dadositem = {};
        dadositem["data_hash"] = msg.item.item_hash;
      }
      dadositem["data_sabor"] = codsabor;
      dadositem["data_tamanho"] = msg.item.item_tamanhoid;
      dadositem["data_qtdsabor"] = msg.item.item_qtdsabor;
      dadositem["data_bordas"] = msg.item.item_borda;
      if(msg.item.item_obs) dadositem["data_obs"] = msg.item.item_obs;
      $("#cont_mont_lanche").data("dadositem", msg.item);
    }
    
    if (msg.item_compositions) dadositem['data_compositions'] = msg.item_compositions; 
    if (msg.item_compositionsAdd) dadositem['data_compositionsAdd'] = msg.item_compositions; 
    $("#cont_mont_lanche").data("dadosdoitematual", dadositem);
  }

  await updateValuesCompositionsTotalOrderDesktop();
}

function acoesObservacoes(dadositem, dadosacao, acao, elemento) {
  var dados = {
    dadositem: dadositem,
    dadosacao: dadosacao,
    acao: acao,
  };
  var codtarget = false;
  if (elemento != undefined) {
    codtarget = elemento.data("target-combo");
  }
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/observacoes/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    hideLoading();
    if (msg.res === true) {
      peencheDadosRetorno(msg, codtarget);
      atualizaPrecoMostrar(codtarget, msg.item);
      if (codtarget != false) {
        $(".btnobs_montmodal." + codtarget).trigger("click");
      } else {
        if (redir_item === true) {
          //document.location.href = '/montar/pizza/'+msg.item.item_cod;
          // objeto ou string - title
          window.history.pushState(
            "Pizza",
            "Pizza",
            "/montar/pizza/" + msg.item.item_cod
          );
          redir_item = false;
          rendPizzaFormaPizza(msg.item);
        } else {
          rendPizzaFormaPizza(msg.item);
        }

      }
    } else if (msg.res === false) {
      if(msg.erro_msg != undefined){
        $("#negative").trigger("click");
        Swal({
            type: "error",
            title: "Oops..",
            html: msg.erro_msg,
            onClose: () => {
                document.location.reload();
            }
        }); 
      }
    } else {

    }
  });
}

async function atualizaPrecoMostrar(targetaba, dadositem) {
  if (targetaba != false) {
    var preco = dadositem.item_preco;
    $(".precotitleitem." + targetaba).text(" - R$ " + parseReal(preco));
    $(".precotitleitem." + targetaba).data('price', preco);
    await updateValuesCompositionsTotalOrderDesktop();
  }
}

function acoesBorda(dadositem, dadosacao, acao, elemento) {
  var dados = {
    dadositem: dadositem,
    dadosacao: dadosacao,
    acao: acao,
  };

  var codtarget = false;
  if (elemento != undefined) {
    codtarget = elemento.data("target-combo");
  }

  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/borda/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    hideLoading();
    if (msg.res === true) {
      peencheDadosRetorno(msg, codtarget);
      atualizaPrecoMostrar(codtarget, msg.item);
      if (codtarget != false) {
        $(".btnbrd_montmodal." + codtarget).trigger("click");
      } else {
        if (redir_item === true) {
          //document.location.href = '/montar/pizza/'+msg.item.item_cod;
          // objeto ou string - title
          window.history.pushState(
            "Pizza",
            "Pizza",
            "/montar/pizza/" + msg.item.item_cod
          );
          redir_item = false;
          rendPizzaFormaPizza(msg.item);
        } else {
          rendPizzaFormaPizza(msg.item);
          checkBordaselected();
        }
      }
    } else if (msg.res === false) {
      if(msg.erro_msg != undefined){
        $("#negative").trigger("click");
        Swal({
          type: "error",
          title: "Oops..",
          html: msg.erro_msg,
          onClose: () => {
            document.location.reload();
          }
        }); 
      }
    } else {

    }
  });
}

function acoesMassa(dadositem, dadosacao, acao, elemento) {
  var dados = {
    dadositem: dadositem,
    dadosacao: dadosacao,
    acao: acao,
  };



  var codtarget = false;
  if (elemento != undefined) {
    codtarget = elemento.data("target-combo");
  }
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/massa/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    if (msg.res === true) {
      peencheDadosRetorno(msg, codtarget);
      atualizaPrecoMostrar(codtarget, msg.item);
      if (codtarget != false) {
        $(".btnmss_montmodal." + codtarget).trigger("click");
      } else {
        if (redir_item === true) {
          //document.location.href = '/montar/pizza/'+msg.item.item_cod;
          window.history.pushState(
            "Pizza",
            "Pizza",
            "/montar/pizza/" + msg.item.item_cod
          );
          redir_item = false;
          rendPizzaFormaPizza(msg.item);
        } else {
          rendPizzaFormaPizza(msg.item);
          $("#negative").trigger("click");
        }
      }
    } else if (msg.res === false) {
      if(msg.erro_msg != undefined){
        $("#negative").trigger("click");
        Swal({
            type: "error",
            title: "Oops..",
            html: msg.erro_msg,
            onClose: () => {
                document.location.reload();
            }
        }); 
      }
    } else {

    }
  });
}

/*
 * Organiza dados para executar a ação
 *
 * @param json dadositem
 * @param json dadosacao
 * @param string acao
 * @returns none
 */
function acoesInsumos(dadositem, dadosacao, acao, elemento, quantidade = 1) {
  let dados_sabor = get_dadossabor(dadosacao.sabor);
  var dados = {
    dadositem: dadositem,
    dadosacao: dadosacao,
    acao: acao,
    qtd: quantidade,
    cod_sessao: dados_sabor.sabor_sessaoid
  };

  //processaAcoesInsumos(dados, elemento);
  var codtarget = false;
  if (elemento != undefined) {
    codtarget = elemento.data("target-combo");
  }
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/insumos/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    hideLoading();
    if (msg.res === true) {
      peencheDadosRetorno(msg, codtarget);
      atualizaPrecoMostrar(codtarget, msg.item);
      if (codtarget != false) {
        rendIngredientesSabor_1(codtarget, dadosacao.sabor);
      } else {
        rendPizzaFormaPizza(msg.item, "insumo");
        if (acao == "excluir" || acao == "adicionar") {
          $(
            ".linkpizza.openlistasabores_dsk[data-pedaco='" +
              dadosacao.pedaco +
              "']"
          ).trigger("click");
        }
      }

      if(msg.msg){
        Swal({
          type: "warning",
          title: "Oops..",
          html: msg.msg,
        }); 
      }
    } else if (msg.res === false) {
      if(msg.erro_msg != undefined){
        $("#negative").trigger("click");
        Swal({
          type: "error",
          title: "Oops..",
          html: msg.erro_msg,
          onClose: () => {
            document.location.reload();
          }
        });
        return; 
      }
      Swal({
        type: "error",
        title: "Oops..",
        html: 'Ocorreu um erro, atualize a página e tente novamente.',
        onClose: () => {
          document.location.reload();
        }
      }); 
    } else {

    }
  });
}

/*
 *
 * @param {type} dadositem
 * @param {type} dadosacao
 * @param {type} acao
 * @param {type} elemento
 * @returns {undefined}
 */
function atualizarTamanho(dadositem, dadosacao, acao, elemento) {
  return new Promise((resolve, reject) => {
    var dados = {
      dadositem: dadositem,
      dadosacao: dadosacao,
      acao: acao,
    };
  
    var bordaNome = 'Borda';
    var qtdBordasAntes = 0;
    if (dadositem.data_bordas != undefined && dadositem.data_bordas != false) {
      qtdBordasAntes = dadositem.data_bordas.length; //qtd bordas antes de trocar o tamanho
      if(dadositem.data_bordas[0].item_bordanome != undefined && dadositem.data_bordas[0].item_bordanome != false){
        bordaNome =  dadositem.data_bordas[0].item_bordanome.substr(0, dadositem.data_bordas[0].item_bordanome.indexOf(':')); 
      }
    }
  
    var codtarget = false;
    if (elemento != undefined) {
      codtarget = elemento.data("target-combo");
    }
    $.ajax({
      method: "POST",
      url: "/exec/montadoritem/tamanho/",
      data: dados,
      dataType: "json",
    }).done(function (msg) {
      if (msg.res === true) {
        resetArrayCompositionsItem();
        peencheDadosRetorno(msg, codtarget);
  
        var qtdBordasDepois = 0;
        if (msg.item.item_borda != undefined && msg.item.item_borda != false){
          qtdBordasDepois = msg.item.item_borda.length; //qtd bordas após a troca de tamanho
        }
  
        if (codtarget != false) {
          peencheMontadorItem(codtarget);
  
          if(qtdBordasAntes != qtdBordasDepois){
            //Verifica se as bordas foram removidas ao trocar para um tamanho que suportava menos qtd de bordas
            Swal({
                type: 'info',
                title: 'Atenção - ' + bordaNome + '(s) Removido(s)',
                html: 'O tamanho selecionado não permite essa quantidade de '+ bordaNome +'. Por favor, selecione novamente.',
                onClose: () => {
                  if(msg.ing_add_removido && msg.ing_add_removido == true) {
                    Swal({
                      type: 'warning',
                      title: 'Tamanho Alterado',
                      html: 'Todos os ingredientes adicionais foram removidos. Por favor, adicione novamente.',
                    });
                    resolve();
                    return;
                  }
                }
            });
          }
  
        } else {
          if(qtdBordasAntes != qtdBordasDepois){
              //Verifica se as bordas foram removidas ao trocar para um tamanho que suportava menos qtd de bordas
              Swal({
                  type: 'info',
                  title: 'Atenção - ' + bordaNome + '(s) Removido(s)',
                  html: 'O tamanho selecionado não permite essa quantidade de '+ bordaNome +'. Por favor, selecione novamente.',
                  onClose: () => {
                    if (redir_item === true) {
                      window.history.pushState(
                        "Pizza",
                        "Pizza",
                        "/montar/pizza/" + msg.item.item_cod
                      );
                      redir_item = false;
                      rendPizzaFormaPizza(msg.item);
                    } else {
                      rendPizzaFormaPizza(msg.item);
                      $("#negative").trigger("click");
                    }
                    if(msg.ing_add_removido && msg.ing_add_removido == true) {
                      Swal({
                        type: 'warning',
                        title: 'Tamanho Alterado',
                        html: 'Todos os ingredientes adicionais foram removidos. Por favor, adicione novamente.',
                      });
                      resolve();
                      return;
                    }
                  }
              });
          } else {
            if (redir_item === true) {
              window.history.pushState(
                "Pizza",
                "Pizza",
                "/montar/pizza/" + msg.item.item_cod
              );
              redir_item = false;
              rendPizzaFormaPizza(msg.item);
            } else {
              rendPizzaFormaPizza(msg.item);
              $("#negative").trigger("click");
            }
            if(msg.ing_add_removido && msg.ing_add_removido == true) {
              Swal({
                type: 'warning',
                title: 'Tamanho Alterado',
                html: 'Todos os ingredientes adicionais foram removidos. Por favor, adicione novamente.',
              });
              resolve();
              return;
            }
          }
        }
        if(msg.ing_add_removido && msg.ing_add_removido == true) {
          Swal({
            type: 'warning',
            title: 'Tamanho Alterado',
            html: 'Todos os ingredientes adicionais foram removidos. Por favor, adicione novamente.',
          });
        }
        resolve();
        return;
      }

      Swal({
          type: "error",
          title: "Oops..",
          html: msg.msg,
          onClose: () => {
            document.location.reload();
          }
      });    
      reject();  
    });
  })
}

function atualizarQtdSabor(dadositem, dadosacao, acao, elemento) {
  var dados = {
    dadositem: dadositem,
    dadosacao: dadosacao,
    acao: acao,
  };
  var codtarget = false;
  if (elemento != undefined) {
    codtarget = elemento.data("target-combo");
  }
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/quantidadesabor/",
    data: dados,
    dataType: "json",
  }).done(function (msg) {
    if (msg.res === true) {    
      peencheDadosRetorno(msg, codtarget);
      if (codtarget != false) {
        peencheMontadorItem(codtarget);
      } else {
        if (redir_item === true) {
          //document.location.href = '/montar/pizza/'+msg.item.item_cod;
          window.history.pushState(
            "Pizza",
            "Pizza",
            "/montar/pizza/" + msg.item.item_cod
          );
          redir_item = false;
          rendPizzaFormaPizza(msg.item);
        } else {
          rendPizzaFormaPizza(msg.item);
          $("#negative").trigger("click");
        }
      }
    } else if (msg.res === false) {
      if(msg.erro_msg != undefined){
        Swal({
            type: "error",
            title: "Oops..",
            html: msg.erro_msg,
            onClose: () => {
              document.location.reload();
            }
        }); 
      }
    } else {

    }
  });
}

function buscaItemMontador(dadositem) {
  /*var dadositem = {
        coditem: "",
        codtaman: "",
        codtipo: "",
        hashitem:""
    };*/

  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/abriritem/",
    data: dadositem,
    dataType: "json",
  }).done(function (msg) {
    if (msg.res === true) {
      rendAbrirItem(msg.dados);
    } else if (msg.res === false) {
      //document.location.reload();
    } else {
    }
  });
}

function get_dadosSessao(id) {
  var cntsessao = sessoes_itens.length;
  for (var i = 0; i < cntsessao; i++) {
    if (sessoes_itens[i].sessao_id == id) {
      return sessoes_itens[i];
    }
  }
  return false;
}

function reendInfoCombo(alldados, hash) {
  var dados = alldados.info;
  var datafid = alldados.fid;
  dados.fidelidade = datafid != undefined ? datafid : "N";
  dados.cod_resgate = alldados.cod_resgate != undefined ? alldados.cod_resgate : false;

  var precom =
    dados.combo_preco === null ? "" : "- R$ " + parseReal(dados.combo_preco);
  $("#montador_combo").data("combo-infos", dados);
  $("#montador_combo").data("combo-hash", hash);
  $(".nome_docombo").text(dados.combo_nome);
  $(".preco_combo").text(precom);
  $(".descricao_combo").text(dados.combo_descricao);

  if (alldados.combo != undefined) {
    if (alldados.combo.preco != undefined) {
      $(".preco_combo").text(" - R$ " + parseReal(alldados.combo.preco));
    }
  }

  if (dados.combo_modelo === "COMBINADO") {
    reendCorpoCombinado(alldados.itens, hash);
  } else if (dados.combo_modelo === "PADRAO") {
    $("#montador_combo").removeClass("combocombinado");
    reendAbasCombo(alldados.itens, hash);
  }
}

function editar_reendInfoCombo(alldados, hash) {
  var dados = alldados.info;
  var precom = "";
  if (dados.combo_preco != undefined) {
    precom =
      dados.combo_preco === null ? "" : "- R$ " + parseReal(dados.combo_preco);
  }

  $("#montador_combo").data("combo-infos", dados);
  $("#montador_combo").data("combo-hash", hash);
  $(".nome_docombo").text(dados.combo_nome);
  $(".preco_combo").text(precom);
  $(".descricao_combo").text(dados.combo_descricao);

  if (dados.combo_modelo === "COMBINADO") {
    reendCorpoCombinado(alldados.itens, hash);
    //reendCorpoCombinado(true);
  } else if (dados.combo_modelo === "PADRAO") {
    editar_reendAbasCombo(alldados.itens, hash);
  }
}
/*
function editar_reendInfoCombo(dados,hash){    
    var precom = (dados.combo_preco === null)? "" : "- R$ " + parseReal(dados.combo_preco);    
    $("#montador_combo").data("combo-infos",dados);
    $("#montador_combo").data("combo-hash",hash);
    $(".nome_docombo").text(dados.combo_nome);
    $(".preco_combo").text(precom);
    $(".descricao_combo").text(dados.combo_descricao);
}
*/
//sabor_ingrediente_nomeingrediente
function get_strListaIngred(arrListaing) {
  var contings = arrListaing.length;
  var strings = "";
  for (var i = 0; i < contings; i++) {
    strings += arrListaing[i].sabor_ingrediente_nomeingrediente;
    strings = i + 1 === contings ? strings : strings + ", ";
  }
  return strings;
}

function get_saboresSessao(codsessao) {
  var arrsaboressessao = [];
  var cntsabsessao = 0;
  var cntsabores = sabores_itens.length;
  for (var t = 0; t < cntsabores; t++) {
    if (sabores_itens[t].sabor_sessaoid == codsessao) {
      arrsaboressessao[cntsabsessao] = sabores_itens[t].sabor_id;
      cntsabsessao++;
    }
  }
  return arrsaboressessao;
}

function get_tamanhoPadraoSessao(codsessao) {
  var arrsaboressessao = [];
  var cntsabsessao = 0;
  var cntsabores = tamahos_itens.length;
  for (var t = 0; t < cntsabores; t++) {
    if (
      tamahos_itens[t].tamanho_sessaoid == codsessao &&
      tamahos_itens[t].tamanho_padrao == "S"
    ) {
      arrsaboressessao[cntsabsessao] = { ID: tamahos_itens[t].tamanho_id };
      cntsabsessao++;
    }
  }
  return arrsaboressessao;
}

function reendListaSabores(sabores, codtarget, tamanhos, pedaco, addsabor) {
  addsabor = addsabor !== undefined && addsabor !== false ? " addsabor " : "";
  pedaco = pedaco == undefined ? 1 : pedaco;

  var conf = $("#" + codtarget).data("combo-confitem");
  var dadosatl = $("#" + codtarget).data("dadosdoitematual");
  var qtdtamanho = 0;

  if (conf !== false) {
    qtdtamanho = tamanhos.length;
  } else {
    qtdtamanho = 1;
  }
  // se item faz uso do montador
  var nomesessao = "";

  var contsabores = sabores.length;
  var contlistasabores = sabores_itens.length;
  var htmcont = "";

  if (qtdtamanho > 0) {
    var otamanho = null;
    if (conf == false) {
      var codsessao = get_sessaoSabor(dadosatl.data_sabor[0]);
      if (typeof itemSettings != "undefined" && itemSettings) {
        sabores = itemSettings["SABORES"];
      } else {
        sabores = get_saboresSessao(codsessao);
      }

      contsabores = sabores.length;
      otamanho = dadosatl.data_tamanho;
    } else {
      otamanho = tamanhos[0].ID;
    }
    if ($(".selecttamitem." + codtarget).length > 0) {
      var tmatl = $(".selecttamitem." + codtarget).val();
      otamanho = tmatl != undefined ? tmatl : otamanho;
    }
    let lista_sabores_combo = [];
    for (var i = 0; i < contsabores; i++) {
      var idsabor = sabores[i];
      for (var y = 0; y < contlistasabores; y++) {
        if (
          sabores_itens[y].sabor_dispcardapio === "S" ||
          comboopen_createdit == true
        ) {
          let idsaborlista = sabores_itens[y].sabor_id;
          if (idsaborlista == idsabor) {
            lista_sabores_combo.push(sabores_itens[y]);
          }
        }
      }
    }
    let tipo_ordenacao = lista_sabores_combo[0].sessao_tipoordenacao;
    lista_sabores_combo = ordenaListaProdutoCompostoComboDesktop(tipo_ordenacao, lista_sabores_combo, otamanho);

    for(let y = 0; y < lista_sabores_combo.length; y++){
      var idsaborlista = lista_sabores_combo[y].sabor_id;
      var nomefoto = lista_sabores_combo[y].sabor_fotonome;
      var idfoto = lista_sabores_combo[y].sabor_fotoid;
      var nomesabor = lista_sabores_combo[y].sabor_nome;
      var listaingreds = get_strListaIngred(
        lista_sabores_combo[y].sabor_ingredientes
      );

      let tag_prod = "";
      let tag_prod_color = "#ff0000";

      if(lista_sabores_combo[y]["sabor_tag"]){
        tag_prod = lista_sabores_combo[y]["sabor_tag"]; 
        tag_prod_color = lista_sabores_combo[y]["sabor_tagcor"];
      }

      let htmlTagProd = tag_prod != "" ? `<span class='tag_prod' style='background-color:${tag_prod_color}'>${tag_prod}</span>` : "";

      var codtamaho = null;
      if (
        lista_sabores_combo[y].sabor_precostamanhos != undefined &&
        lista_sabores_combo[y].sabor_precostamanhos.length > 0
      ) {
        var qtdtamsab = lista_sabores_combo[y].sabor_precostamanhos.length;
        for (var t = 0; t < qtdtamsab; t++) {
          if (
            otamanho ==
            lista_sabores_combo[y].sabor_precostamanhos[t]
              .sabor_precotamanhos_codtamanho
          ) {
            codtamaho = otamanho;
          }
        }

        if (codtamaho != null) {
          nomesessao = lista_sabores_combo[y].sabor_sessaonome;

          htmcont +=
            "<li class='itensdelistasabores " +
            codtarget +
            addsabor +
            "' data-target-combo='" +
            codtarget +
            "' data-codsabor='" +
            idsaborlista +
            "' data-pdc='" +
            pedaco +
            "' data-codtamanho='" +
            codtamaho +
            "'>" +
            "<div class='fotoimglistasabor'>" +
            "<img src='" +
            urlsfiles.imagens +
            "produtos/" +
            idfoto +
            "/60/" +
            nomefoto +
            "' />" +
            "</div>" +
            `<span class='nomesaborlistasabores'><span>${nomesabor}</span> ${htmlTagProd}` +
            " <small class='precosaborlistasabores'></small></span>" +
            "<p class='descingredienteslistasabores'>" +
            listaingreds +
            "</p>" +
            "</li>";
        }
      }
    }
  }

  if (!htmcont && qtdtamanho > 0) {
    Swal({
      type: "warning",
      title: "Oops..",
      html: "Combo indisponível no momento, tente novamente mais tarde."
    }); 
    $("#montDorCombo").modal("hide");
    return;
  }

  var htmcontbusca =
    "<li class='itensdelistasaboresbusca'>" +
    "<input type='text' class='buscarsabor' placeholder='Buscar Sabor' />" +
    "</li>";

  var htmcontm =
    "<div class='listadesaboresescolher " +
    codtarget +
    "'>" +
    "<div class='nano'>" +
    //+           "<span class='titulolistasabores "+codtarget+"'>"+nomesessao+"</span>"
    "<span class='titulolistasabores " +
    codtarget +
    "'><img src='" +
    urlsfiles.media +
    vsao +
    "/img/fechar_side_esq.png' class='close_sidemenu_esq'/>Selecione um Sabor</span>" +
    "<ul class='listacomsabores nano-content  " +
    codtarget +
    "'>" +
    htmcontbusca +
    htmcont +
    "</ul>" +
    "</div>" +
    "</div>" +
    "<div class='listadeingredientes_opc " +
    codtarget +
    "'>" +
    "<div class='nano'>" +
    "<span class='topoeditaringred'><img src='" +
    urlsfiles.media +
    vsao +
    "/img/fechar_side.png' class='close_sidemenu'/>Editar ingredientes</span>" +
    "<span class='titulo_nomesabor " +
    codtarget +
    "'></span>" +
    "<div class='content_listaingredientes nano-content'>" +
    "<ul class='listacomingredientessabor " +
    codtarget +
    "'></ul>" +
    "<ul class='listacomingredientessabor_opc " +
    codtarget +
    "'></ul>" +
    "</div>" +
    "</div>" +
    "</div>" +
    "<div class='listademassas " +
    codtarget +
    "'>" +
    "<div class='nano'>" +
    "<span class='topomassa " +
    codtarget +
    "'><img src='" +
    urlsfiles.media +
    vsao +
    "/img/fechar_side.png' class='close_sidemenu'/></span>" +
    "<div class='content_listamassa nano-content'>" +
    "<ul class='listacommassasitem " +
    codtarget +
    "'></ul>" +
    "</div>" +
    "</div>" +
    "</div>" +
    "<div class='listadebordas " +
    codtarget +
    "'>" +
    "<div class='nano'>" +
    "<span class='topoborda " +
    codtarget +
    "'><img src='" +
    urlsfiles.media +
    vsao +
    "/img/fechar_side.png' class='close_sidemenu'/></span>" +
    "<div class='content_listaborda nano-content'>" +
    "<ul class='listacombordasitem " +
    codtarget +
    "'></ul>" +
    "</div>" +
    "</div>" +
    "</div>" +
    "<div class='listadecomposicoes " +
    codtarget +
    "'>" +
    "<div class='nano'>" +
    "<span class='topocomposicoes " +
    codtarget +
    "'><img src='" +
    urlsfiles.media +
    vsao +
    "/img/fechar_side.png' class='close_sidemenu'/></span>" +
    "<div class='content_listacomposicoes nano-content'>" +
    "<ul class='listacomcomposicoesitem " +
    codtarget +
    "'></ul>" +
    "</div>" +
    "</div>" +
    "</div>" +
    "<div class='listadeobservacoes " +
    codtarget +
    "'>" +
    "<div class='nano'>" +
    "<span class='topoobservacoes " +
    codtarget +
    "'><img src='" +
    urlsfiles.media +
    vsao +
    "/img/fechar_side.png' class='close_sidemenu'/></span>" +
    "<div class='content_listaobservacoes nano-content'>" +
    "<ul class='listacomobservacoesitem " +
    codtarget +
    "'></ul>" +
    "</div>" +
    "</div>" +
    "</div>";

  return htmcontm;
}

function htmlMontadorPizza_1s(targetaba) {
  var htmcont =
    "<div class='coluna_esquerda " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' >" +
    "<div class='formapizza " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' ></div>" +
    "</div>" +
    "<div class='coluna_direita " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "' style='width:560px;' >" +
    "<h3 class='tit_itemmont'><span class='nometetleitem " +
    targetaba +
    "' >Nome do Item Escolhido</span> <span class='precotitleitem " +
    targetaba +
    "' ></span></h3>" +
    "<select data-tamanhos='' class='txt selecttamitem " +
    targetaba +
    "' data-tamanhos data-target-combo='" +
    targetaba +
    "'></select>" +
    "<select data-listaqtd='' class='txt selectqtditem " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'></select>" +
    "<div class='clear'></div>" +
    "<div class='ing_modalmont " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'>" +
    "</div>";
  return htmcont;
}

function htmlMontadorPizza_maisd1s(targetaba, contsabores, codtamanho) {
  var htmcont =
    "<div class='coluna_esquerda " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' >" +
    "<div class='formapizza " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' ></div>" +
    "</div>" +
    "<div class='coluna_direita " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "' style='width:560px;' >" +
    "<div>" +
    "<h3 class='tit_itemmont'><span class='nometetleitem " +
    targetaba +
    "' >Nome do Item Escolhido</span> <span class='precotitleitem " +
    targetaba +
    "' ></span></h3>" +
    "<select data-tamanhos='' class='txt selecttamitem " +
    targetaba +
    "' data-tamanhos data-target-combo='" +
    targetaba +
    "'></select>" +
    "<select data-listaqtd='' class='txt selectqtditem " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'></select>" +
    "<a title='' class='btnbrd_montmodal " +
    targetaba +
    "'  data-codtam='" +
    codtamanho +
    "' data-target-combo='" +
    targetaba +
    "'></a>" +
    "<a title='' class='btnmss_montmodal " +
    targetaba +
    "' data-codtam='" +
    codtamanho +
    "'  data-target-combo='" +
    targetaba +
    "'></a>" +
    "</div>" +
    "<div class='clear'></div>" +
    "<div class='listsaboresdapizza listasabores " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'></div>" +
    "<a title='Observações' class='btnobs_montmodal " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'>Observações</a>" +
    "</div>";
  return htmcont;
}

function htmlMontadorItem_maisd1s(targetaba, contsabores, codtamanho) {
  var htmcont =
    "<div class='coluna_esquerda " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' >" +
    "<img class='img_modalmont " +
    targetaba +
    " '  data-target-combo='" +
    targetaba +
    "' src=''/>" +
    "</div>" +
    "<div class='coluna_direita " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "' >" +
    "<h3 class='tit_itemmont'><span class='nometetleitem " +
    targetaba +
    "' >Nome do Item Escolhido</span> <span class='precotitleitem " +
    targetaba +
    "' ></span></h3>" +
    "<select data-tamanhos='' class='txt selecttamitem " +
    targetaba +
    "' data-tamanhos data-target-combo='" +
    targetaba +
    "'></select>" +
    "<select data-listaqtd='' class='txt selectqtditem " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'></select>" +
    "<div class='clear'></div>" +
    "<div class=' listasabores " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'></div>" +
    "<a title='' class='btnbrd_montmodal " +
    targetaba +
    "'  data-codtam='" +
    codtamanho +
    "' data-target-combo='" +
    targetaba +
    "'></a>" +
    "<a title='' class='btnmss_montmodal " +
    targetaba +
    "' data-codtam='" +
    codtamanho +
    "'  data-target-combo='" +
    targetaba +
    "'></a>" +
    "<a title='Observações' class='btnobs_montmodal " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'>Observações</a>" +
    "</div>";
  return htmcont;
}

function htmlMontadorItem_1s(targetaba) {
  var htmcont =
    "<div class='coluna_esquerda " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' >" +
    "<img class='img_modalmont " +
    targetaba +
    " openlistasabores' data-pdc='1'  data-target-combo='" +
    targetaba +
    "' src=''/>" +
    "</div>" +
    "<div class='coluna_direita " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'  >" +
    "<h3 class='tit_itemmont'><span class='nometetleitem " +
    targetaba +
    "' >Nome do Item Escolhido</span> <span class='precotitleitem " +
    targetaba +
    "' ></span></h3>" +
    "<select data-tamanhos='' class='txt selecttamitem " +
    targetaba +
    "' data-tamanhos data-target-combo='" +
    targetaba +
    "'></select>" +
    "<select data-listaqtd='' class='txt selectqtditem " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'></select>" +
    "<div class='clear'></div>" +
    "<div class='ing_modalmont " +
    targetaba +
    "' data-target-combo='" +
    targetaba +
    "'>" +
    "</div>" +
    "</div>";
  return htmcont;
}

function get_ingredtxt(ingreds, acao) {
  var txtings = null;
  if (ingreds !== false && ingreds.length > 0) {
    txtings = "";
    var cnt = ingreds.length;
    for (var t = 0; t < cnt; t++) {
      txtings += acao + ingreds[t].ingrediente_nome;
      txtings = t + 1 < cnt ? txtings + "," : txtings;
    }
  }
  return txtings;
}

function getNomeBorda(codtamanho) {
  var cnt = bordas_itens.length;
  for (var f = 0; f < cnt; f++) {
    var tansbd = bordas_itens[f].borda_precotamanho;
    if (tansbd.length > 0) {
      for (var fs = 0; fs < tansbd.length; fs++) {
        var idtam = tansbd[fs].precotamannho_tamanhoid;
        if (codtamanho == idtam) {
          var nomebd = bordas_itens[f].borda_nome;
          var nomesplit = nomebd.split(":");
          if (nomesplit.length > 1) {
            return nomesplit[0];
          }
        }
      }
    }
  }
  return false;
}

function getNomeMassa(codtamanho) {
  var cnt = massas_itens.length;
  for (var f = 0; f < cnt; f++) {
    var tansbd = massas_itens[f].massa_precotamanho;
    if (tansbd.length > 0) {
      for (var fs = 0; fs < tansbd.length; fs++) {
        var idtam = tansbd[fs].precotamannho_tamanhoid;
        if (codtamanho == idtam) {
          var nomebd = massas_itens[f].massa_nome;
          var nomesplit = nomebd.split(":");
          if (nomesplit.length > 1) {
            return nomesplit[0];
          }
        }
      }
    }
  }
  return false;
}

function getNomeObservacoes(codtamanho) {
  var cnt = observacoes_itens.length;
  for (var f = 0; f < cnt; f++) {
    var tansbd = observacoes_itens[f].observacoes_precotamanho;
    if (tansbd.length > 0) {
      for (var fs = 0; fs < tansbd.length; fs++) {
        var idtam = tansbd[fs].precotamannho_tamanhoid;
        if (codtamanho == idtam) {
          return true;
        }
      }
    }
  }
  return false;
}

async function peencheMontadorItem(targetaba) {
  var dadosdoitematual = $("#" + targetaba).data("dadosdoitematual");
  var dadositem = $("#" + targetaba).data("dadositem");
  var confitem = $("#" + targetaba).data("combo-confitem");
  var tamanhosposiveis = [];

  var opcionaisitem = {};

  var hash = dadosdoitematual.data_hash;
  var contsabores = parseInt(dadositem.item_qtdsabor);
  var conttamanhositem = 0;
  var dadossessao = get_dadosSessao(dadositem.item_sessaoid);
  var codtamanho = dadositem.item_tamanhoid;
  let obs_texto = dadositem.item_obs ? dadositem.item_obs : "";
  let obs_texto_localstorage = localStorage.getItem('ed_obsitem');
  obs_texto = obs_texto_localstorage ? obs_texto_localstorage : obs_texto;
  item_tamanho = codtamanho;
  let ocultarIngredientes = dadossessao.sabor_sessao_ocultaringredientes && dadossessao.sabor_sessao_ocultaringredientes == 'S' ? true : false;
  ocultarIngredientes = 
    !ocultarIngredientes 
    && dadossessao.sessao_ocultaringredientes 
    && dadossessao.sessao_ocultaringredientes == 'S' 
    && (!dadossessao.sessao_paginamontador || dadossessao.sessao_paginamontador.indexOf("montarpizza") == -1)
    ? true : false; 

  let htmlUpsellMontadorPadrao = $(`.coluna_direita.${targetaba} #upsell_montador_padrao_desktop`).html();

  let qtdSaboresTamanho = tamahos_itens.filter(x => x['tamanho_id'] == codtamanho);
  if (typeof qtdSaboresTamanho[0]['tamanho_qtdsabormaxima'] != 'object') {
    qtdSaboresTamanho[0]['tamanho_qtdsabormaxima'] = JSON.parse(qtdSaboresTamanho[0]['tamanho_qtdsabormaxima']).map(x => x.toString());
  }

  qtdSaboresTamanho = qtdSaboresTamanho.length > 0 ? qtdSaboresTamanho[0]['tamanho_qtdsabormaxima'] : [contsabores.toString()];
  if (!qtdSaboresTamanho.includes(contsabores.toString())) {
    contsabores = qtdSaboresTamanho.filter(x => x > contsabores.toString())[0];
  }

  let compositionsItem = () => {
    if (compositionsItemMontador.compositions.length > 0) return compositionsItemMontador.compositions;
    if (dadositem.item_compositions) {
      return dadositem.item_compositions.map(element => {
        return {
          amount: element.amount,
          compositionId: element.compositionId,
          price: element.price,
          catCompositionId: element.categoryId ? element.categoryId : element.catCompositionId ? element.catCompositionId : 0
        }
      });
    }

    return [];
  }

  let compositionsItemAdd = () => {
    if (compositionsItemMontador.add.length > 0) return compositionsItemMontador.add;
    if (dadositem.item_compositionsAdd) {
      return dadositem.item_compositionsAdd.map(element => {
        return {
          amount: element.amount,
          compositionId: element.compositionId,
          price: element.price,
          catCompositionId: element.categoryId ? element.categoryId : element.catCompositionId ? element.catCompositionId : 0
        }
      });
    }

    return [];
  }

  compositionsItemMontador.compositions = compositionsItem();
  compositionsItemMontador.add = compositionsItemAdd();

  let permite_addingredientes =  dadossessao.sessao_addingrediente ? dadossessao.sessao_addingrediente : 'N';
  if(permite_addingredientes == 'N') {
    permite_addingredientes =  dadossessao.permite_addingredientes ? dadossessao.permite_addingredientes : 'N';
  }

  if(dadossessao.sessao_permite_obsmanual && dadossessao.sessao_permite_obsmanual === 'S') {
    permite_obsmanual = 'S';
  } else {
    permite_obsmanual = 'N';
  }

  if (confitem == false) {
    //tamanhosposiveis = get
  } else {
    tamanhosposiveis = confitem.tamanhos;
    opcionaisitem = confitem.opcionais;
    conttamanhositem = tamanhosposiveis.length;
  }

  var per_bordas = false;
  var per_massa = false;
  var per_obs = false;
  var per_ingred = false;
  let catCompositions = await getCatCompositionsBySessionAndSize(dadositem.item_sessaoid, codtamanho);
  
  if (confitem == undefined || confitem == false) {
    per_bordas = getNomeBorda(codtamanho);
    per_ingred = true;
    per_obs = getNomeObservacoes(codtamanho);
    per_massa = getNomeMassa(codtamanho);
  } else if (opcionaisitem !== false) {
    per_bordas =
      opcionaisitem.BORDAS !== undefined && opcionaisitem.BORDAS.COBRAR !== "NP"
        ? getNomeBorda(codtamanho)
        : per_bordas;
    per_ingred =
      opcionaisitem.INGREDIENTE !== undefined &&
      opcionaisitem.INGREDIENTE.COBRAR !== "NP"
        ? true
        : per_ingred;
    per_obs =
      opcionaisitem.OBSERVASOES !== undefined &&
      opcionaisitem.OBSERVASOES.COBRAR !== "NP"
        ? getNomeObservacoes(codtamanho)
        : per_obs;
    per_massa =
      opcionaisitem.MASSA !== undefined && opcionaisitem.MASSA.COBRAR !== "NP"
        ? getNomeMassa(codtamanho)
        : per_massa;
  }

  per_ingred = permite_addingredientes == 'S' ? true : false;
  per_ingred = ocultarIngredientes ? false : per_ingred;

  if (
    dadossessao.sessao_paginamontador === "montarpizza" ||
    dadossessao.sessao_paginamontador === "montarpizzaquadrada"
  ) {
    var dados = {
      tamanho: codtamanho,
      qtdsabor: contsabores,
      targetcombo: targetaba,
      sabor: [],
      montador: dadossessao.sessao_paginamontador,
    };

    if (contsabores === 1) {
      $(".itensdelistasabores." + targetaba).removeClass("addsabor");

      var htmlmt_1s = htmlMontadorPizza_1s(targetaba);
      $(".montador_doitem." + targetaba).html(htmlmt_1s);

      var codsabor = dadositem.sabores[0].item_saborid;
      var nomesabor = dadositem.sabores[0].item_sabornome;

      var ftid = dadositem.sabores[0].item_saborfotoid;
      var ftnome = dadositem.sabores[0].item_saborfotonome;

      // reenderiza lista de tamanhos
      rendTamanhosSelect_(tamanhosposiveis, codtamanho, targetaba);
      // reenderiza lista de ingredientes
      rendIngredientesSabor_1(targetaba, codsabor);
      $(".nometetleitem." + targetaba).text(nomesabor);

      if (conttamanhositem > 1) {
        $(".selecttamitem." + targetaba).show();
      } else {
        $(".selecttamitem." + targetaba).hide();
      }

      dados.sabor[0] = {
        pedaco: 1,
        codsabor: codsabor,
        nome: nomesabor,
        urlfoto: "" + urlsfiles.imagens + "produtos/" + ftid + "/240/" + ftnome,
        montador: dadossessao.sessao_paginamontador,
      };

      rendPizzaMontagem(dados);

      var htmbtn_opc = "";
      if (per_ingred === true) {
        htmbtn_opc +=
          "<a title='Adicionar Opcionais' class='btnopc_montmodal " +
          targetaba +
          "' data-target-combo='" +
          targetaba +
          "' data-pdc='1' data-codsabor='" +
          codsabor +
          "'>+ Adicionar Ingredientes</a>";
      }
      if (
        per_bordas !== false &&
        get_bordadasessao(dadossessao.sessao_id, codtamanho) !== false
      ) {
        htmbtn_opc +=
          "<a title='" +
          per_bordas +
          "' class='btnbrd_montmodal " +
          targetaba +
          "' data-codtam='" +
          codtamanho +
          "' data-target-combo='" +
          targetaba +
          "'>Selecionar " +
          per_bordas +
          "</a>";
      }
      if (
        per_massa !== false &&
        get_massasdasessao(dadossessao.sessao_id, codtamanho) !== false
      ) {
        htmbtn_opc +=
          "<a title='" +
          per_massa +
          "' class='btnmss_montmodal " +
          targetaba +
          "' data-codtam='" +
          codtamanho +
          "' data-target-combo='" +
          targetaba +
          "'>Selecionar " +
          per_massa +
          "</a>";
      }

      if (catCompositions) {
        for (let i = 0; i < catCompositions.length; i++) {
          htmbtn_opc += `<a title='${catCompositions[i]['NOME']}' data-catcompositionid='${catCompositions[i]['ID']}' class='btncomposicao_montmodal ${targetaba}' data-codtam='${codtamanho}' data-target-combo='${targetaba}'>${catCompositions[i]['NOME']}</a>`;
        }
      }

      if (
        per_obs !== false &&
        get_observacoesdasessao(dadossessao.sessao_id, codtamanho) !== false
      ) {
        htmbtn_opc +=
          "<a title='Observações' class='btnobs_montmodal " +
          targetaba +
          "' data-codtam='" +
          codtamanho +
          "' data-target-combo='" +
          targetaba +
          "'>Observações</a>";
      }

      $(".btnopc_montmodal." + targetaba).remove();
      $(".btnbrd_montmodal." + targetaba).remove();
      $(".btnmss_montmodal." + targetaba).remove();
      $(".btnobs_montmodal." + targetaba).remove();

      if (htmbtn_opc !== "") {
        $(".ing_modalmont." + targetaba).after(htmbtn_opc);
      }
    } else {
      var htmlmt_maisd1s = htmlMontadorPizza_maisd1s(
        targetaba,
        contsabores,
        codtamanho
      );
      $(".montador_doitem." + targetaba).html(htmlmt_maisd1s);

      $(".nometetleitem." + targetaba).text(dadossessao.sessao_nome);

      rendTamanhosSelect_(tamanhosposiveis, codtamanho, targetaba);
      if (conttamanhositem > 1) {
        $(".selecttamitem." + targetaba).show();
      } else {
        $(".selecttamitem." + targetaba).hide();
      }
      var lstsabores = "";

      var cnsab = 0;
      for (var ui = 1; ui <= contsabores; ui++) {
        if (dadositem.sabores.length > cnsab) {
          if (dadositem.sabores[cnsab].item_saborpedaco == ui) {
            var codsabor = dadositem.sabores[cnsab].item_saborid;
            var nomesabor = dadositem.sabores[cnsab].item_sabornome;
            var ftid = dadositem.sabores[cnsab].item_saborfotoid;
            var ftnome = dadositem.sabores[cnsab].item_saborfotonome;

            var ingsem = get_ingredtxt(
              dadositem.sabores[cnsab].item_saboringredrem,
              "s/ "
            );
            var ingcom = get_ingredtxt(
              dadositem.sabores[cnsab].item_saboringredcom,
              "c/ "
            ); 

            var listopcing = ingsem !== null ? ingsem + ";" : "";
            listopcing += ingcom !== null ? ingcom : "";
            var listadosingsopc = "";
            dados.sabor[cnsab] = {
              pedaco: ui,
              codsabor: codsabor,
              nome: nomesabor,
              urlfoto:
                "" + urlsfiles.imagens + "produtos/" + ftid + "/240/" + ftnome,
            };

            lstsabores +=
              "<div class='box_selectsabor'>" +
              "<span class='lbl_saborqtd'>Sabor " +
              ui +
              ":</span>" +
              "<a href='#' class='selectnovosabor " +
              targetaba +
              "' data-target-combo='" +
              targetaba +
              "' data-pdc='" +
              ui +
              "'  >" +
              nomesabor +
              listadosingsopc +
              "</a>";
            if(per_ingred === true){
              lstsabores +=
                "<a title='Adicionar Opcionais' class='btnopc_montmodal " +
                targetaba +
                "' data-target-combo='" +
                targetaba +
                "' data-pdc='" +
                ui +
                "' data-codsabor='" +
                codsabor +
                "'> Ingredientes</a>";
            }
            +"</div>";
            cnsab++;
          } else {
            lstsabores +=
              "<div class='box_selectsabor'>" +
              "<span class='lbl_saborqtd'>Sabor " +
              ui +
              ":</span>" +
              "<a href='#' class='selectnovosabor " +
              targetaba +
              "' data-target-combo='" +
              targetaba +
              "' data-pdc='" +
              ui +
              "'  >Selecione um sabor</a>" +
              "</div>";
          }
        } else {
          lstsabores +=
            "<div class='box_selectsabor'>" +
            "<span class='lbl_saborqtd'>Sabor " +
            ui +
            ":</span>" +
            "<a href='#' class='selectnovosabor " +
            targetaba +
            "' data-target-combo='" +
            targetaba +
            "' data-pdc='" +
            ui +
            "'  >Selecione um sabor</a>" +
            "</div>";
        }
      }

      $(".listasabores." + targetaba).html(lstsabores);

      rendPizzaMontagem(dados);
      if (
        per_bordas === false ||
        get_bordadasessao(dadossessao.sessao_id, codtamanho) === false
      ) {
        $(".btnbrd_montmodal." + targetaba).remove();
      } else {
        $(".btnbrd_montmodal." + targetaba).attr("title", per_bordas);
        $(".btnbrd_montmodal." + targetaba).text("Selecionar " + per_bordas);
      }

      if (
        per_massa === false ||
        get_massasdasessao(dadossessao.sessao_id, codtamanho) === false
      ) {
        $(".btnmss_montmodal." + targetaba).remove();
      } else {
        $(".btnmss_montmodal." + targetaba).attr("title", per_massa);
        $(".btnmss_montmodal." + targetaba).text("Selecionar " + per_massa);
      }

      if (
        per_obs === false ||
        get_observacoesdasessao(dadossessao.sessao_id, codtamanho) === false
      ) {
        $(".btnobs_montmodal." + targetaba).remove();
      }
    }
  } else {
    if (confitem == false) {
      tamanhosposiveis = get_tamanhos_dosabor(
        dadositem.sabores[0].item_saborid
      );
      conttamanhositem = tamanhosposiveis.length;
    }

    if (typeof itemSettings != "undefined" && itemSettings) {
      if (itemSettings["OPCIONAIS"]["INGREDIENTE"]["COBRAR"] == "NP") {
        per_ingred = false;
      }

      if (itemSettings["OPCIONAIS"]["BORDAS"]["COBRAR"] == "NP") {
        per_bordas = false;
      }

      if (itemSettings["OPCIONAIS"]["OBSERVASOES"]["COBRAR"] == "NP") {
        per_obs = false;
      }

      configComposicoesItemCombo = itemSettings["OPCIONAIS"]["COMPOSICOES"];
    }

    var nometitulo = "";
    var precosabor = 0;
    var quantidadeitens = "01";
    if (contsabores === 1) {
      $(".itensdelistasabores." + targetaba).removeClass("addsabor");

      var htmlmt_1s = htmlMontadorItem_1s(targetaba);
      $(".montador_doitem." + targetaba).html(htmlmt_1s);

      var codsabor = dadositem.sabores[0].item_saborid;
      var nomesabor = dadositem.sabores[0].item_sabornome;
      nometitulo = dadositem.sabores[0].item_sabornome;
      var ftid = dadositem.sabores[0].item_saborfotoid;
      var ftnome = dadositem.sabores[0].item_saborfotonome;
      precosabor = dadositem.item_preco;
      quantidadeitens = dadositem.item_quantidade;
      // reenderiza lista de tamanhos
      rendTamanhosSelect_(tamanhosposiveis, codtamanho, targetaba);
      // reenderiza lista de ingredientes
      rendIngredientesSabor_1(targetaba, codsabor);
      $(".nometetleitem." + targetaba).text(nomesabor);
      $(".img_modalmont." + targetaba).attr(
        "src",
        "" + urlsfiles.imagens + "produtos/" + ftid + "/240/" + ftnome
      );
      if (conttamanhositem > 1) {
        $(".selecttamitem." + targetaba).show();
      } else {
        $(".selecttamitem." + targetaba).hide();
      }

      var htmbtn_opc = "";
      if (per_ingred === true) {
        htmbtn_opc +=
          "<a title='Adicionar Opcionais' class='btnopc_montmodal " +
          targetaba +
          "' data-target-combo='" +
          targetaba +
          "' data-pdc='1' data-codsabor='" +
          codsabor +
          "'>+ Adicionar Ingredientes</a>";
      }
      if (
        per_bordas !== false &&
        get_bordadasessao(dadossessao.sessao_id, codtamanho) !== false
      ) {
        htmbtn_opc +=
          "<a title='" +
          per_bordas +
          "' class='btnbrd_montmodal " +
          targetaba +
          "' data-codtam='" +
          codtamanho +
          "' data-target-combo='" +
          targetaba +
          "'>Selecionar " +
          per_bordas +
          "</a>";
      }
      if (
        per_massa !== false &&
        get_massasdasessao(dadossessao.sessao_id, codtamanho) !== false
      ) {
        htmbtn_opc +=
          "<a title='" +
          per_massa +
          "' class='btnmss_montmodal " +
          targetaba +
          "' data-codtam='" +
          codtamanho +
          "' data-target-combo='" +
          targetaba +
          "'>Selecionar " +
          per_massa +
          "</a>";
      }

      if (catCompositions) {
        for (let i = 0; i < catCompositions.length; i++) {
          htmbtn_opc += `<a title='${catCompositions[i]['NOME']}' data-catcompositionid='${catCompositions[i]['ID']}' class='btncomposicao_montmodal ${targetaba}' data-codtam='${codtamanho}' data-target-combo='${targetaba}'>${catCompositions[i]['NOME']}</a>`;
        }
      }

      if (
        per_obs !== false &&
        get_observacoesdasessao(dadossessao.sessao_id, codtamanho) !== false
      ) {
        htmbtn_opc +=
          "<a title='Observações' class='btnobs_montmodal " +
          targetaba +
          "' data-codtam='" +
          codtamanho +
          "' data-target-combo='" +
          targetaba +
          "'>Observações</a>";
      }

      $(".ing_modalmont." + targetaba).after(htmbtn_opc);
    } else {
      var htmlmt_maisd1s = htmlMontadorItem_maisd1s(
        targetaba,
        contsabores,
        codtamanho
      );
      $(".montador_doitem." + targetaba).html(htmlmt_maisd1s);

      var ftid = dadositem.sabores[0].item_saborfotoid;
      var ftnome = dadositem.sabores[0].item_saborfotonome;
      precosabor = dadositem.item_preco;
      quantidadeitens = dadositem.item_quantidade;
      $(".nometetleitem." + targetaba).text(dadossessao.sessao_nome);
      $(".img_modalmont." + targetaba).attr(
        "src",
        "" + urlsfiles.imagens + "produtos/" + ftid + "/240/" + ftnome
      );
      // reenderiza lista de tamanhos
      rendTamanhosSelect_(tamanhosposiveis, codtamanho, targetaba);
      if (conttamanhositem > 1) {
        $(".selecttamitem." + targetaba).show();
      } else {
        $(".selecttamitem." + targetaba).hide();
      }
      var lstsabores = "";

      var cnsab = 0;
      for (var ui = 1; ui <= $(`.selectqtditem.${targetaba}`).val(); ui++) {
        if (dadositem.sabores.length > cnsab) {
          if (dadositem.sabores[cnsab].item_saborpedaco == ui) {
            var codsabor = dadositem.sabores[cnsab].item_saborid;
            var nomesabor = dadositem.sabores[cnsab].item_sabornome;
            nometitulo = nometitulo != "" ? nometitulo + " / " : nometitulo;
            nometitulo += dadositem.sabores[cnsab].item_sabornome;
            lstsabores +=
              "<div class='box_selectsabor'>" +
              "<span class='lbl_saborqtd'>Sabor " +
              ui +
              ":</span>" +
              "<a href='#' class='selectnovosabor " +
              targetaba +
              "' data-target-combo='" +
              targetaba +
              "' data-pdc='" +
              ui +
              "'  >" +
              nomesabor +
              "</a>";
              if (!ocultarIngredientes) {
                lstsabores += "<a title='Adicionar Opcionais' class='btnopc_montmodal " +
                  targetaba +
                  "' data-target-combo='" +
                  targetaba +
                  "' data-pdc='" +
                  ui +
                  "' data-codsabor='" +
                  codsabor +
                  "'> Ingredientes</a>";
              } 
            lstsabores += "</div>";
            cnsab++;
          } else {
            lstsabores +=
              "<div class='box_selectsabor'>" +
              "<span class='lbl_saborqtd'>Sabor " +
              ui +
              ":</span>" +
              "<a href='#' class='selectnovosabor " +
              targetaba +
              "' data-target-combo='" +
              targetaba +
              "' data-pdc='" +
              ui +
              "'  >Selecione um sabor</a>" +
              "</div>";
          }
        } else {
          lstsabores +=
            "<div class='box_selectsabor'>" +
            "<span class='lbl_saborqtd'>Sabor " +
            ui +
            ":</span>" +
            "<a href='#' class='selectnovosabor " +
            targetaba +
            "' data-target-combo='" +
            targetaba +
            "' data-pdc='" +
            ui +
            "'  >Selecione um sabor</a>" +
            "</div>";
        }
      }

      nometitulo = dadossessao.sessao_nome + " - " + nometitulo;

      $(".listasabores." + targetaba).html(lstsabores);

      if (
        per_bordas === false ||
        get_bordadasessao(dadossessao.sessao_id, codtamanho) === false
      ) {
        $(".btnbrd_montmodal." + targetaba).remove();
      } else {
        $(".btnbrd_montmodal." + targetaba).attr("title", per_bordas);
        $(".btnbrd_montmodal." + targetaba).text("Selecionar " + per_bordas);
      }

      if (
        per_massa === false ||
        get_massasdasessao(dadossessao.sessao_id, codtamanho) === false
      ) {
        $(".btnmss_montmodal." + targetaba).remove();
      } else {
        $(".btnmss_montmodal." + targetaba).attr("title", per_massa);
        $(".btnmss_montmodal." + targetaba).text("Selecionar " + per_massa);
      }

      let htmlCompositions = "";
      if (catCompositions) {
        for (let i = 0; i < catCompositions.length; i++) {
          htmlCompositions += `<a title='${catCompositions[i]['NOME']}' data-catcompositionid='${catCompositions[i]['ID']}' class='btncomposicao_montmodal ${targetaba}' data-codtam='${codtamanho}' data-target-combo='${targetaba}'>${catCompositions[i]['NOME']}</a>`;
        }
      }

      $(htmlCompositions).insertBefore(`.btnobs_montmodal.${targetaba}`);

      if (
        per_obs === false ||
        get_observacoesdasessao(dadossessao.sessao_id, codtamanho) === false
      ) {
        $(".btnobs_montmodal." + targetaba).remove();
      }
    }
    if (confitem == false) {
      $(".tit_modalmont").text(dadossessao.sessao_nome);
      await updatePricesCompositionsCat();
      let totalPriceCompositions = await getTotalPriceAllCompositionsItem(dadositem["item_compositions"], dadositem["item_compositionsAdd"]);
      $(".precotitleitem." + targetaba).text(" - R$ " + parseReal(precosabor - totalPriceCompositions));
      $(".precotitleitem." + targetaba).data('price', precosabor - totalPriceCompositions);
      await updateValuesCompositionsTotalOrderDesktop();

      var htmlqtd =
        "<p>Quantidade:</p>" +
        "<div class='qtd_modalcont'>" +
        "<a href='#' title='Remover' class='menosum_item " +
        targetaba +
        "'  data-target-combo='" +
        targetaba +
        "' >-</a>" +
        "<input type='text' value='" +
        quantidadeitens +
        "' readonly='true'></input>" +
        "<a href='#' title='Adicionar' class='maisum_item " +
        targetaba +
        "'  data-target-combo='" +
        targetaba +
        "' >+</a>" +
        "<div class='clear'></div>" +
        "</div>";
      $(".img_modalmont." + targetaba).after(htmlqtd);

      if(permite_obsmanual === 'S') {
        let input_observacao = `
          <textarea rows="3" id="obspedido" class="obs_item" placeholder="Alguma observação?" style="width: 80%;margin-top: 15px;" maxlength="140">${obs_texto}</textarea>
        `;
        $(".coluna_direita." + targetaba).append(input_observacao);
      }

      var html_btncomprar =
        " <div class='clear'></div><a title='Adicionar ao carrinho' id='btncomprar_montmodal' class='comprar_item " +
        targetaba +
        "'  data-target-combo='" +
        targetaba +
        "' ><span class='icon-comprarmodal'></span>Comprar!</a> ";
      $(".coluna_direita." + targetaba).append(html_btncomprar);
    }
  }

  if (htmlUpsellMontadorPadrao && htmlUpsellMontadorPadrao.length > 0) {
    $(`<div id="upsell_montador_padrao_desktop">${htmlUpsellMontadorPadrao}</div>`).insertBefore(`.comprar_item.${targetaba}`);
  }
}

function editar_reendAbasCombo(alldados, hash) {
  //dados[i].
  var dados = alldados;
  var htmabas = "";
  var htmcont = "";
  var firstaba = false;
  var cntitens = dados.length;
  var arrRandAbas = [];
  var arrRandAbas2 = [];
  //itempronto
  for (var i = 0; i < cntitens; i++) {
    let qtdMaxIngredAdicionais = '';
    if (dados[i].tamanhos[0] !== undefined) {
      qtdMaxIngredAdicionais = 0;
      if (dados[i].tamanhos[0].QTDMAX_INGRED_OPCIONAIS !== undefined && dados[i].tamanhos[0].QTDMAX_INGRED_OPCIONAIS !== null) {
        qtdMaxIngredAdicionais = dados[i].tamanhos[0].QTDMAX_INGRED_OPCIONAIS;
      }
    }
    var idsessao = dados[i].sessao;
    var editavel = dados[i].editavel;
    var dadossessao = get_dadosSessao(idsessao);
    var tamanhos = dados[i].tamanhos;
    var sabores = dados[i].sabores;
    var qtditem = dados[i].quantidade;

    if (dadossessao !== false) {
      var qtdtamanhos = tamanhos.length;

      var tipomontador = dadossessao.sessao_paginamontador;
      var icone = dadossessao.sessao_icone;
      var tipoicone = dadossessao.sessao_tipoicone;
      var nome = dadossessao.sessao_nome;
      var targetaba = gerarValor(8, true, true);
      arrRandAbas[i] = targetaba;
      firstaba = firstaba === false ? targetaba : firstaba;

      var url_imgimagem = urlsfiles.imagens.substr(
        0,
        urlsfiles.imagens.length - 1
      );

      htmabas +=
        "<a href='#' data-combo-abatarget='" +
        targetaba +
        "' class='abacombo' title='" +
        nome +
        "'><img src='" +
        url_imgimagem +
        icone +
        "'/>" +
        nome +
        "</a>";
      htmcont +=
        "<div class='cont_abascombo' data-combo-confitem data-dadosdoitematual data-dadositem data-qtd_max_ingred_adic='" + qtdMaxIngredAdicionais + "' id='" +
        targetaba +
        "'>";

      if (editavel === true) {
        htmcont +=
          "<div class='esmaecer_montador " +
          targetaba +
          "' style='display: none;' data-target-combo='" +
          targetaba +
          "'></div>";

        htmcont += reendListaSabores(sabores, targetaba, tamanhos);

        htmcont +=
          "<div class='montador_doitem " +
          targetaba +
          "'  data-target-combo='" +
          targetaba +
          "'>";

        arrRandAbas2[i] = targetaba;
        htmcont += "</div>";
      } else {
        htmcont += reendListaItemSimples(
          sabores,
          qtditem,
          targetaba,
          tamanhos,
          dados[i].itensescolhidos
        );
      }

      htmcont += "</div>";
    }
  }

  $(".abas_combo").html(htmabas);
  $("#content_combo").html(htmcont);
  $(".esmaecer_montador").show();
  $(".abacombo[data-combo-abatarget='" + firstaba + "']").trigger("click");

  arrRandAbas.forEach(function (value, idx) {
    $("#" + value).data("combo-confitem", dados[idx]);
    if (dados[idx].itempronto != undefined) {
      $("#" + value).data("dadositem", dados[idx].itempronto);
      $(".listadesaboresescolher").css("left", "-900px");
      $(".esmaecer_montador").hide();
      peencheMontadorItem(value);
      var msg = {
        item: dados[idx].itempronto,
      };
      msg.item.hash = dados[idx].itempronto.hash;
      peencheDadosRetorno(msg, value);
    }
  });

  let configCombo = $("#" + firstaba).data("combo-confitem");
  if (configCombo) {
    configComposicoesItemCombo = configCombo.opcionais.hasOwnProperty('COMPOSICOES') ? configCombo.opcionais['COMPOSICOES'] : {};
  }
}

function reendAbasCombo(dados, hash) {
  var htmabas = "";
  var htmcont = "";
  var firstaba = false;
  var cntitens = dados.length;
  var arrRandAbas = [];
  var arrListaUmSabor = [];
  var cnt_umsabor = 0;
  var arrListaUmItem = [];
  var cnt_umitem = 0;
  for (var i = 0; i < cntitens; i++) {
    let qtdMaxIngredAdicionais = '';
    if (dados[i].tamanhos[0] !== undefined) {
      qtdMaxIngredAdicionais = 0;
      if (dados[i].tamanhos[0].QTDMAX_INGRED_OPCIONAIS !== undefined && dados[i].tamanhos[0].QTDMAX_INGRED_OPCIONAIS !== null) {
        qtdMaxIngredAdicionais = dados[i].tamanhos[0].QTDMAX_INGRED_OPCIONAIS;
      }
    }
    var idsessao = dados[i].sessao;
    var editavel = dados[i].editavel;
    var dadossessao = get_dadosSessao(idsessao);
    var tamanhos = dados[i].tamanhos;
    var sabores = dados[i].sabores;
    var qtditem = dados[i].quantidade;

    if (dadossessao !== false) {
      var qtdtamanhos = tamanhos.length;

      var tipomontador = dadossessao.sessao_paginamontador;
      var icone = dadossessao.sessao_icone;
      var tipoicone = dadossessao.sessao_tipoicone;
      var nome = dadossessao.sessao_nome;
      var targetaba = gerarValor(8, true, true);
      arrRandAbas[i] = targetaba;
      firstaba = firstaba === false ? targetaba : firstaba;

      var overf = "";
      if (editavel !== true) {
        overf = "style='overflow-y: auto;'";
      }

      var url_imgimagem = urlsfiles.imagens.substr(
        0,
        urlsfiles.imagens.length - 1
      );

      htmabas +=
        "<a href='#' data-combo-abatarget='" +
        targetaba +
        "' class='abacombo' title='" +
        nome +
        "'><img src='" +
        url_imgimagem +
        icone +
        "'/>" +
        nome +
        "</a>";
      htmcont +=
        "<div class='cont_abascombo' data-combo-confitem data-dadosdoitematual data-dadositem data-qtd_max_ingred_adic='" + qtdMaxIngredAdicionais + "' id='" +
        targetaba +
        "' " +
        overf +
        ">";

      if (editavel === true) {
        htmcont +=
          "<div class='esmaecer_montador noitemselected blackesm " +
          targetaba +
          "'  data-target-combo='" +
          targetaba +
          "'></div>";

        htmcont += reendListaSabores(sabores, targetaba, tamanhos);
        if (sabores.length === 1) {
          arrListaUmSabor[cnt_umsabor] = targetaba;
          cnt_umsabor++;
        }
        htmcont +=
          "<div class='montador_doitem " +
          targetaba +
          "'  data-target-combo='" +
          targetaba +
          "'>";

        htmcont += "</div>";
      } else {
        htmcont += reendListaItemSimples(sabores, qtditem, targetaba, tamanhos);
        if (sabores.length === 1) {
          arrListaUmItem[cnt_umitem] = { qtd: qtditem, targ: targetaba };
          cnt_umitem++;
        }
      }
      htmcont += "</div>";
    }
  }

  $(".abas_combo").html(htmabas);
  $("#content_combo").html(htmcont);
  $(".esmaecer_montador").show();
  $(".abacombo[data-combo-abatarget='" + firstaba + "']").trigger("click");
  arrRandAbas.forEach(function (value, idx) {
    $("#" + value).data("combo-confitem", dados[idx]);
  });

  let configCombo = $("#" + firstaba).data("combo-confitem");
  if (configCombo) {
    configComposicoesItemCombo = configCombo.opcionais.hasOwnProperty('COMPOSICOES') ? configCombo.opcionais['COMPOSICOES'] : {};
  }

  comboiniciado_ok = null;
  excCb = false;
  listcqCb = [];
  intVcombo = null;
  cbqtd = 0;
  cbqtdatl = 0;

  var classExec = [];
  var cntClEx = 0;

  for (var i = 0; i < arrListaUmSabor.length; i++) {
    classExec[cntClEx] = ".itensdelistasabores." + arrListaUmSabor[i];
    cntClEx++;
    //$(".itensdelistasabores."+arrListaUmSabor[i]).trigger("click");
  }

  for (var i = 0; i < arrListaUmItem.length; i++) {
    var qtds = arrListaUmItem[i].qtd;
    if(qtds > 1){
      classExec[cntClEx] = ".addmaisitem."+arrListaUmItem[i].targ;
      cntClEx++;
      //$(".addmaisitem."+arrListaUmItem[i].targ).trigger("click");
    }
    else{
      classExec[cntClEx] = ".addunicoitem." + arrListaUmItem[i].targ;
      cntClEx++;
      //$(".addunicoitem."+arrListaUmItem[i].targ).trigger("click");
    }
  }

  listcqCb = classExec;
  cbqtd = classExec.length;

  intVcombo = setInterval(function () {
    if (comboiniciado_ok === true || excCb === false) {
      listcqCb[cbqtdatl];
      $(listcqCb[cbqtdatl]).trigger("click", true);
      cbqtdatl++;
      if (cbqtdatl == cbqtd) {
        clearInterval(intVcombo);
      }
      excCb = true;
    }
  }, 30);

  $(".nano").nanoScroller();
}

function reendListaItemSimples(sabores, qtd, targetaba, tamanhos, itensesc) {
  const textAmountItems = qtd > 1 ? `${qtd} ITENS` : "1 ITEM";
  let htmlitemsimples = `<span class="amountItemsComboDesktop">SELECIONE NO TOTAL, ${textAmountItems} </span>`;

  var cntsabores = sabores.length;
  var cntitemsabores = sabores_itens.length;
  var selectitem = "";
  var itensescolhidos = [];
  var cntitem = 0;
  if (itensesc != undefined) {
    itensescolhidos = itensesc;
    cntitem = itensescolhidos.length;
  }
  let lista_itens_combo = [];
  for (var i = 0; i < cntsabores; i++) {
    for (var y = 0; y < cntitemsabores; y++) {
      var cdsabor = sabores_itens[y].sabor_id;
      if (sabores_itens[y].sabor_id == sabores[i]) {
        lista_itens_combo.push(sabores_itens[y]);
      }
    }
  }
  let tipo_ordenacao = lista_itens_combo[0].sessao_tipoordenacao;
  lista_itens_combo = ordenaListaProdutoSimplesPromosDesktop(tipo_ordenacao, lista_itens_combo);
  for(let y = 0; y < lista_itens_combo.length; y++){
    let cdsabor =  lista_itens_combo[y].sabor_id;
    var cdtipo = lista_itens_combo[y].sabor_sessaoid;
    var nomeiitem = lista_itens_combo[y].sabor_nome;
    var fotonomeitem = lista_itens_combo[y].sabor_fotonome;
    var fotoiditem = lista_itens_combo[y].sabor_fotoid;
    const image = lista_itens_combo[y].sabor_image;
    let tag_prod = "";
    let tag_prod_color = "#ff0000";

    if(lista_itens_combo[y]["sabor_tag"]){
      tag_prod = lista_itens_combo[y]["sabor_tag"]; 
      tag_prod_color = lista_itens_combo[y]["sabor_tagcor"];
    }

    let htmlTagProd = tag_prod != "" ? `<span class='tag_prod' style='background-color:${tag_prod_color}'>${tag_prod}</span>` : ""

    let caminhofoto = `${urlsfiles.imagens}produtos/${fotoiditem}/150/${fotonomeitem}`;
    if (image) caminhofoto = `${urlsfiles.imagens}itens/${image}`;
    if (qtd == 1) {
      if (tamanhos !== false) {
        var cnttamthis = tamanhos.length;
        var tamanhossabor = lista_itens_combo[y].sabor_precostamanhos.length;
        for (var ij = 0; ij < cnttamthis; ij++) {
          var idtamth = tamanhos[ij].ID;
          for (var sh = 0; sh < tamanhossabor; sh++) {
            var tmsh =
              lista_itens_combo[y].sabor_precostamanhos[sh]
                .sabor_precotamanhos_codtamanho;
            if (tmsh == idtamth) {
              selectitem = "";
              for (var hs = 0; hs < cntitem; hs++) {
                if (
                  itensescolhidos[hs].item == cdsabor &&
                  itensescolhidos[hs].tamanho == tmsh
                ) {
                  selectitem = "selecionado";
                }
              }

              var nometm =
                lista_itens_combo[y].sabor_precostamanhos[sh]
                  .sabor_precotamanhos_nometamanho;

              if(lista_itens_combo[y].sabor_sessao_controlarestoque === 'S' && parseInt(lista_itens_combo[y].sabor_estoque) <= 0) {
                htmlitemsimples +=
                "<div class='item_simp_comb zeroitem item_indisponivel"; 
              } else {
                htmlitemsimples +=
                "<div class='item_simp_comb zeroitem "; 
              }
              htmlitemsimples +=  selectitem +
                " " +
                targetaba +
                "' data-target-combo='" +
                targetaba +
                "' >" +
                "<img src='" +
                caminhofoto +
                "' alt='" +
                nomeiitem +
                "' width='110'/>" +
                htmlTagProd +
                "<p>" +
                nomeiitem +
                "</p>" +
                "<a href='#' title='Selecionar' class='btn_sel_item addunicoitem " +
                targetaba +
                "'  data-target-combo='" +
                targetaba +
                "' data-codtam='" +
                idtamth +
                "' data-codsabor='" +
                cdsabor +
                "' data-codtipo='" +
                cdtipo +
                "' >Selecionar</a>" +
                "</div>";
            }
          }
        }
      } else {
        selectitem = "";
        for (var hs = 0; hs < cntitem; hs++) {
          if (itensescolhidos[hs].item == cdsabor) {
            selectitem = "selecionado";
          }
        }
        if(lista_itens_combo[y].sabor_sessao_controlarestoque === 'S' && parseInt(lista_itens_combo[y].sabor_estoque) <= 0) {
          htmlitemsimples +=
          "<div class='item_simp_comb zeroitem item_indisponivel"; 
        } else {
          htmlitemsimples +=
          "<div class='item_simp_comb zeroitem "; 
        }
        htmlitemsimples += selectitem +
          " " +
          targetaba +
          "' data-target-combo='" +
          targetaba +
          "' >" +
          "<img src='" +
          caminhofoto +
          "' alt='" +
          nomeiitem +
          "' width='110'/>" +
          htmlTagProd +
          "<p>" +
          nomeiitem +
          "</p>"; 
          if(lista_itens_combo[y].sabor_sessao_controlarestoque === 'S' && parseInt(lista_itens_combo[y].sabor_estoque) <= 0) {
            htmlitemsimples += "<a href='#' title='Selecionar' class='btn_sel_item txt_indisponivel" +
            "' >Indisponível</a>";
          } else {
            htmlitemsimples += "<a href='#' title='Selecionar' class='btn_sel_item addunicoitem " +
            targetaba +
            "'  data-target-combo='" +
            targetaba +
            "' data-codtam='false' data-codsabor='" +
            cdsabor +
            "' data-codtipo='" +
            cdtipo +
            "' >Selecionar</a>";
          }
          htmlitemsimples += "</div>";
      }
    } else {
      var qtditematl = 0;
      var zritem = "zeroitem";
      if (cntitem > 0) {
        zritem += " inativo";
      }
      if (tamanhos !== false) {
        var cnttamthis = tamanhos.length;
        var tamanhossabor = lista_itens_combo[y].sabor_precostamanhos.length;
        for (var ij = 0; ij < cnttamthis; ij++) {
          var idtamth = tamanhos[ij].ID;
          for (var sh = 0; sh < tamanhossabor; sh++) {
            var tmsh =
              lista_itens_combo[y].sabor_precostamanhos[sh]
                .sabor_precotamanhos_codtamanho;
            if (tmsh == idtamth) {
              for (var hs = 0; hs < cntitem; hs++) {
                if (
                  itensescolhidos[hs].item == cdsabor &&
                  itensescolhidos[hs].tamanho == tmsh
                ) {
                  zritem = "";
                  qtditematl = itensescolhidos[hs].qtd;
                }
              }

              var nometm =
                lista_itens_combo[y].sabor_precostamanhos[sh]
                  .sabor_precotamanhos_nometamanho;

              htmlitemsimples +=
                "<div class='item_simp_comb " +
                zritem +
                " " +
                targetaba +
                "' data-target-combo='" +
                targetaba +
                "'>" +
                "<img src='" +
                caminhofoto +
                "' alt='" +
                nomeiitem +
                "(" +
                nometm +
                ")' width='110'/>" +
                htmlTagProd +
                "<p>" +
                nomeiitem +
                "(" +
                nometm +
                ")</p>" +
                "<div class='qtd_modalcont_item " +
                targetaba +
                "' data-target-combo='" +
                targetaba +
                "'>" +
                "<a href='#' title='Remover' class='addmenositem " +
                targetaba +
                "'  data-target-combo='" +
                targetaba +
                "' data-codtam='" +
                idtamth +
                "' data-codsabor='" +
                cdsabor +
                "' data-codtipo='" +
                cdtipo +
                "'  >-</a>" +
                "<input type='text' class='valqtditem comboItemAmount inteiro' maxlength='3' value='" +
                qtditematl +
                "' data-target-combo='" +
                targetaba +
                "'></input>" +
                "<a href='#' class='addmaisitem " +
                targetaba +
                "' title='Adicionar'  data-target-combo='" +
                targetaba +
                "' data-codtam='" +
                idtamth +
                "' data-codsabor='" +
                cdsabor +
                "' data-codtipo='" +
                cdtipo +
                "' >+</a>" +
                "<div class='clear'></div>" +
                "</div>" +
                "</div>";
            }
          }
        }
      } else {
        for (var hs = 0; hs < cntitem; hs++) {
          if (itensescolhidos[hs].item == cdsabor) {
            zritem = "";
            qtditematl = itensescolhidos[hs].qtd;
          }
        }
        
        if(lista_itens_combo[y].sabor_sessao_controlarestoque === 'S' && parseInt(lista_itens_combo[y].sabor_estoque) <= 0) {
          htmlitemsimples +=
            "<div class='item_simp_comb item_indisponivel ";
        } else {
          htmlitemsimples +=
            "<div class='item_simp_comb ";
        }
        htmlitemsimples += zritem +
          " " +
          targetaba +
          "' data-target-combo='" +
          targetaba +
          "'>" +
          "<img src='" +
          caminhofoto +
          "' alt='" +
          nomeiitem +
          "' width='110'/>" +
          htmlTagProd +
          "<p>" +
          nomeiitem +
          "</p>";
          if(lista_itens_combo[y].sabor_sessao_controlarestoque === 'S' && parseInt(lista_itens_combo[y].sabor_estoque) <= 0) {
            htmlitemsimples += '<span style="display: flex;justify-content: center;color: red;font-size: 0.7rem;">Indisponível</span>';
          } else {
            htmlitemsimples += "<div class='qtd_modalcont_item " +
            targetaba +
            "' data-target-combo='" +
            targetaba +
            "'>" +
            "<a href='#' title='Remover' class='addmenositem " +
            targetaba +
            "' data-target-combo='" +
            targetaba +
            "' data-codtam='false' data-codsabor='" +
            cdsabor +
            "' data-codtipo='" +
            cdtipo +
            "'  >-</a>" +
            "<input type='text' class='valqtditem comboItemAmount inteiro' maxlength='3' value='" +
            qtditematl +
            "' data-target-combo='" +
            targetaba +
            "'></input>" +
            "<a href='#' title='Adicionar' class='addmaisitem " +
            targetaba +
            "' data-target-combo='" +
            targetaba +
            "' data-codtam='false' data-codsabor='" +
            cdsabor +
            "' data-codtipo='" +
            cdtipo +
            "' >+</a>" +
            "<div class='clear'></div>" +
            "</div>";
          }
          htmlitemsimples += "</div>";
      }
    } 
  }
  return htmlitemsimples;
}

function alteraFormaEntrega(forma_entrega, dados_combo, hash_combo, fidelidade = false){
  let ajxFormaEntrega = $.ajax({
    url: "/exec/minha-conta/formaenvio/",
    method: "POST",
    data: {formaentrega: forma_entrega},
    dataType: "json"
  });

  ajxFormaEntrega.done(function(msg){
    get_resumoPedido();
    if(msg.res == true){
      if(fidelidade == true) return;
      openModalCombo(dados_combo)
      return;
    }
    $("#montDorCombo").modal("hide");
    if(msg.nerro && msg.nerro == 'login'){
      Swal({
        type: "error",
        title: "Oops..",
        html: msg.msg,
        onClose: function(){
          document.location.href = "/cadastrar";
        }
      }); 
      return;
    } else {
      if(msg.res != true){
        if(msg.combos_invalidos){
          if(msg.combos_invalidos.length < 1) return;
          let resposta = criaMsgCombosIndisponiveisFormaEntrega(msg.combos_invalidos);
          Swal({
              type: 'warning',
              title: 'Oops...',
              html: resposta
          });
          return;
        }
        Swal({
          type: "error",
          title: "Oops..",
          html: msg.msg
        }); 
      }
    }
  });

  ajxFormaEntrega.fail(function(v1, v2){
    Swal({
        type: 'error',
        title: 'Erro ao Alterar Forma de Entrega',
        text: 'Algo deu errado, verifique sua conexão e tente novamente.'
    });
  });
}

function buscaConfComboMontador(dados, tipo) {
  $(".btnfinaliza_combo").removeClass("ativo");
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/abrircombo/",
    data: dados,
    dataType: "json",
    async: false
  }).done(function (msg) {
    $("#btnfinalizacombo").removeClass("completou");
    if (msg.res === true) {
      if (msg.dados.algum_item_inativo === true) {
        Swal({
          type: 'info',
          title: 'Oops',
          text: `O '${msg.dados.info.combo_nome}' está indisponível hoje!`
        });
        return false;
      }

      const filialFormasEntrega = JSON.parse($('#filialFormasEntrega').val());
      let forma_entrega_combo = msg.dados.info.combo_formaentrega.split(',');
      let forma_entrega_atual = resumo.pedido_formaentrega_cod;

      if(forma_entrega_atual && forma_entrega_combo.indexOf(forma_entrega_atual) == -1){
        let optionsFormaEntrega = {};
        for (let i = 0; i < filialFormasEntrega.length; i++) {
          if (filialFormasEntrega[i] == forma_entrega_atual || forma_entrega_combo.indexOf(filialFormasEntrega[i]) < 0) continue;
          switch (filialFormasEntrega[i]) {
            case 'E':
              optionsFormaEntrega['entrega'] = ['Entrega'];
              break;
            case 'R':
              optionsFormaEntrega['retirar'] = ['Retirar no Local'];
              break;
            case 'C':
              optionsFormaEntrega['consumirlocal'] = ['Consumir no Local'];
              break;
          }
        }

        switch (forma_entrega_atual) {
          case 'E':
            forma_entrega_atual = 'Entrega';
            break;
          case 'R':
            forma_entrega_atual = 'Retirada';
            break;
          case 'C':
            forma_entrega_atual = 'Consumir no Local';
            break;
        }

        if (Object.keys(optionsFormaEntrega).length == 0) {
          Swal({
            type: 'info',
            title: 'Forma de Entrega Inválida',
            html: `Esse combo não é válido para <strong>${forma_entrega_atual}</strong>`
          });
          return;
        }

        Swal({
          title: 'Forma de Entrega Inválida',
          html: `Esse combo não é válido para <strong>${forma_entrega_atual}</strong>, deseja alterar a forma de entrega?`,
          type: 'info',
          showCancelButton: true,
          confirmButtonColor: '#3085d6',
          cancelButtonColor: '#d33',
          confirmButtonText: 'Sim, Alterar',
          cancelButtonText: 'Não',
          input: "select",
          inputOptions: optionsFormaEntrega,
          inputPlaceholder: "Selecione a forma de entrega",
          inputValidator: (value) => {
            if (!value) {
              return "É necessário selecionar uma opção";
            }
            msg.dados['statusCombo'] = 'new';
            alteraFormaEntrega(value, msg.dados, msg.dados.hash);
          }
        })
        return false;
      }
      
      msg.dados['statusCombo'] = 'new';
      openModalCombo(msg.dados)
      return true;
    }
    if(msg.delivery_fechado && msg.delivery_fechado == true){
      Swal({
        type: 'info',
        title: 'Delivery Online - Fechado',
        html: htmlServiceHoursToday
      });
      return;
    }
    if (msg.res === false) {
      if (msg.dados && msg.dados.disabledItems && Object.keys(msg.dados.disabledItems).length > 0) {
        let categoriesDisabled = msg.dados.disabledItems;
        const factoryMsg = function() {
          let categories = Object.keys(categoriesDisabled).map(e => categoriesDisabled[e]);
          let html = "<div style='text-align: left;padding-left:15px;'>";
          for (let i = 0; i < categories.length; i++) {
            html += `<li><strong>${categories[i]}</strong></li>`;
          }

          html += '</div>';
          html = `<span style="text-align: left; display:block;">Os itens das categorias abaixo estão indisponíveis:</span>${html}`
          return html;
        };
  
        Swal({
          type: 'info',
          title: 'Combo Indisponível',
          html: factoryMsg()
        });
        fechaModalUniv(2);
        return;
      }

      Swal({
        type: 'info',
        title: 'Combo Indisponível',
        text: msg.msg,
      });
      fechaModalUniv(2);
    }
  });
}

function rendTamanhosSelect(tamanhospossiveis, codtamanho) {
  $(".selecttamitem").data("tamanhospossiveis", tamanhospossiveis);
  var htmopttamanhos = "";

  var cnttampss = tamanhospossiveis.length;
  var cnttam = tamahos_itens.length;

  for (var i = 0; i < cnttampss; i++) {
    var tampss = tamanhospossiveis[i].tamanho_id;

    for (var y = 0; y < cnttam; y++) {
      var taman = tamahos_itens[y].tamanho_id;

      if (taman == tampss) {
        var nome = tamahos_itens[y].tamanho_nome;
        var img = tamahos_itens[y].tamanho_imagem;
        var padrao = tamahos_itens[y].tamanho_padrao;
        var calzone = tamahos_itens[y].tamanho_calzone;
        var qtdsabor = tamahos_itens[y].qtddsabor;
        var listaqtdsabor = tamahos_itens[y].lista_qtdsabor;
        htmopttamanhos += "<option value='" + taman + "'>" + nome + "</option>";
      }
    }
  }
  $(".selecttamitem").html(htmopttamanhos);
  if (codtamanho != undefined) {
    $(".selecttamitem").val(codtamanho);
    $(".selecttamitem").change();
  }
}

function rendQuantidadeSabores(codtamanho, tamanhos, codtarget) {
  var dadositem = $("#" + codtarget).data("dadositem");
  var qtdstam = dadositem.item_qtdsabor;
  var htmlqtdsabor = "";

  var cnttam = tamahos_itens.length;
  for (var y = 0; y < cnttam; y++) {
    var taman = tamahos_itens[y].tamanho_id;
    if (taman == codtamanho) {
      if (!Array.isArray(tamanhos[0].QTDMAX) && typeof JSON.parse(tamanhos[0].QTDMAX) == 'number') {
        for (var bhs = 0; bhs < tamanhos.length; bhs++) {
          if (codtamanho == tamanhos[bhs].ID) {
            let dados_tamanho = get_tamanho_dados(codtamanho);
            let qtddms = tamanhos[bhs].QTDMAX;
            if (typeof dados_tamanho.tamanho_qtdsabormaxima != 'object') dados_tamanho.tamanho_qtdsabormaxima = JSON.parse(dados_tamanho.tamanho_qtdsabormaxima);
            qtddms = dados_tamanho.tamanho_qtdsabormaxima.includes(qtddms.toString()) ? qtddms : dados_tamanho.tamanho_qtdsabormaxima.slice(-1)[0];

            for (var qt = 1; qt <= qtddms; qt++) {
              if (!dados_tamanho.tamanho_qtdsabormaxima.includes(qt.toString())) continue;
              var selected = "";
              if (qt == qtdstam) {
                selected = " selected='selected' ";
              }
              htmlqtdsabor +=
                "<option " +
                selected +
                " value='" +
                qt +
                "'>" +
                qt +
                " Sabor(es)" +
                "</option>";
            }
            if (qtddms == 1) {
              $(".selectqtditem." + codtarget).hide();
            } else {
              $(".selectqtditem." + codtarget).show();
            }
          }
        }
      } else {
        var listaqtdsabor = tamahos_itens[y].lista_qtdsabor;
        var contqtd = listaqtdsabor.length;
        let hasSelected = false;
        for (var i = 0; i < contqtd; i++) {
          var txtnome = listaqtdsabor[i].text;
          var qtd = listaqtdsabor[i].value;
          var selected = "";
          if (qtd == qtdstam || (!hasSelected && qtd > qtdstam)) {
            hasSelected = true;
            selected = " selected='selected' ";
          }
          htmlqtdsabor +=
            "<option " +
            selected +
            " value='" +
            qtd +
            "'>" +
            txtnome +
            "</option>";
        }
        if (contqtd == 1) {
          $(".selectqtditem." + codtarget).hide();
        } else {
          $(".selectqtditem." + codtarget).show();
        }
      }
    }
  }
  $(".selectqtditem." + codtarget).html(htmlqtdsabor);
}

function rendTamanhosSelect_(tamanhospossiveis, codtamanho, targetaba) {
  //$(".selecttamitem."+targetaba).data("tamanhospossiveis",tamanhospossiveis);
  var htmopttamanhos = "";

  if (typeof itemSettings != "undefined" && itemSettings) {
    tamanhospossiveis = itemSettings["TAMANHOS"];
  }

  var cnttampss = tamanhospossiveis.length;
  var cnttam = tamahos_itens.length;

  for (var i = 0; i < cnttampss; i++) {
    var tampss = tamanhospossiveis[i].ID;

    for (var y = 0; y < cnttam; y++) {
      var taman = tamahos_itens[y].tamanho_id;

      if (taman == tampss) {
        var nome = tamahos_itens[y].tamanho_nome;
        var img = tamahos_itens[y].tamanho_imagem;
        var padrao = tamahos_itens[y].tamanho_padrao;
        var calzone = tamahos_itens[y].tamanho_calzone;
        var qtdsabor = tamahos_itens[y].qtddsabor;
        var listaqtdsabor = tamahos_itens[y].lista_qtdsabor;
        htmopttamanhos += "<option value='" + taman + "'>" + nome + "</option>";
      }
    }
  }
  $(".selecttamitem." + targetaba).html(htmopttamanhos);
  $(".selecttamitem." + targetaba).data("tamanhos", tamanhospossiveis);
  if (codtamanho != undefined) {
    $(".selecttamitem." + targetaba).val(codtamanho);
    rendQuantidadeSabores(codtamanho, tamanhospossiveis, targetaba);
  }
}

function get_precoIngrediente(ingredient, codtamanho, config, qtdsabor) {
  var preco = false;
  if (config == false || config.opcionais.INGREDIENTE.COBRAR !== "NP") {
    const conttaming = ingredient.ingredientes_precotamanho ? ingredient.ingredientes_precotamanho.length : 0;
    var sessaoing = ingredient.ingrediente_sessaoid;
    var dadossss = get_dadosSessao(sessaoing);
    var divisaoing = dadossss.sessao_divisaoingrediente;
    for (var i = 0; i < conttaming; i++) {
      var idtam =
        ingredient.ingredientes_precotamanho[i]
          .ingrediente_precotamannho_tamanhoid;
      if (idtam == codtamanho) {
        preco = 0;
        if (config == false || config.opcionais.INGREDIENTE.COBRAR === "S") {
          var precotam =
            ingredient.ingredientes_precotamanho[i]
              .ingrediente_precotamannho_preco;
          precotam = parseFloat(precotam);
          if (
            qtdsabor != undefined &&
            qtdsabor > 1 &&
            divisaoing !== "INTEIRO"
          ) {
            if (precotam > 0) {
              precotam = precotam / qtdsabor;
            }
          }
          preco = precotam;
        }
      }
    }
  }
  return preco;
}

function rendIngredientesSabor_1(targetaba, codsabor) {
  var dadositem = $("#" + targetaba).data("dadositem");
  var config = $("#" + targetaba).data("combo-confitem");
  var qtdsabor = dadositem.item_qtdsabor;
  var codtamanho = dadositem.item_tamanhoid;
  var ingredientes = [];
  var cntsabores = sabores_itens.length;
  let permite_remover_ingrediente = false;
  let permite_add_ingrediente = false;
  let ocultarIngredientes = false;

  for (var isb = 0; isb < cntsabores; isb++) {
    if (sabores_itens[isb].sabor_id == codsabor) {
      ingredientes = sabores_itens[isb].sabor_ingredientes;
      permite_remover_ingrediente = (sabores_itens[isb].sabor_sessao_removeingrediente && sabores_itens[isb].sabor_sessao_removeingrediente == 'S') ? true : false;
      permite_add_ingrediente = (sabores_itens[isb].sabor_sessao_addingrediente && sabores_itens[isb].sabor_sessao_addingrediente == 'S') ? true : false;
      ocultarIngredientes = 
        sabores_itens[isb].sabor_sessao_ocultaringredientes 
        && sabores_itens[isb].sabor_sessao_ocultaringredientes == 'S' 
        && (!sabores_itens[isb].sessao_paginamontador || sabores_itens[isb].sessao_paginamontador.indexOf("montarpizza") == -1)
        ? true : false;
    }
  }

  if (ocultarIngredientes) return;

  var ingrem = [];
  var ingadd = [];
  let qtd_ingadd = [];
  var sabores = dadositem.sabores;
  if (sabores !== undefined && sabores.length > 0) {
    for (var ih = 0; ih < sabores.length; ih++) {
      if (sabores[ih].item_saboringredcom !== false) {
        for (var ik = 0; ik < sabores[ih].item_saboringredcom.length; ik++) {
          ingadd[ik] = sabores[ih].item_saboringredcom[ik].ingrediente_cod;
          qtd_ingadd[ik] = sabores[ih].item_saboringredcom[ik].ingrediente_qtd;
        }
      }

      if (sabores[ih].item_saboringredrem !== false) {
        for (var ik = 0; ik < sabores[ih].item_saboringredrem.length; ik++) {
          ingrem[ik] = sabores[ih].item_saboringredrem[ik].ingrediente_cod;
        }
      }
    }
  }

  var cnting = ingredientes.length;
  var htmingreds =
    "<p style='color:#000;margin: 0; padding: 3px 0;'>Ingredientes:</p>";
  for (var i = 0; i < cnting; i++) {
    var coding = ingredientes[i].sabor_ingrediente_codingrediente;
    var nomeingredi = ingredientes[i].sabor_ingrediente_nomeingrediente;
    var emfaltaing = ""; //ingredientes[i].ingrediente_emfalta;
    var valrand_ = gerarValor(8, true, true);

    var cheking = "checked";
    var chetached = "";
    if (in_array(coding, ingrem)) {
      cheking = "";
      chetached = " style='text-decoration: line-through;' ";
    }

    htmingreds +=
      "<div class='lst_ings' " +
      chetached +
      ">"; 
    if(permite_remover_ingrediente == true){
      htmingreds += "<input class='magic-checkbox' type='checkbox' name='layout' data-target-combo='" ;
    } else {
      htmingreds += "<input class='magic-checkbox' disabled type='checkbox' name='layout' data-target-combo='" ;
    }
    htmingreds += targetaba +
      "' data-sabor='" +
      codsabor +
      "' data-pedaco='1' id='ing_" +
      valrand_ +
      "' value='" +
      coding +
      "' " +
      cheking +
      "> <label for='ing_" +
      valrand_ +
      "'></label><label class='text nome_ings' for='ing_" +
      valrand_ +
      "'>" +
      nomeingredi +
      "</label></div>";
  }

  if (ingadd.length > 0) {
    for (var td = 0; td < ingadd.length; td++) {
      var cntings = ingredientes_itens.length;
      for (var tr = 0; tr < cntings; tr++) {
        if (ingadd[td] == ingredientes_itens[tr].ingrediente_id) {
          var iding = ingredientes_itens[tr].ingrediente_id;
          var nomeingredi = ingredientes_itens[tr].ingrediente_nome;
          var valrand_ = gerarValor(8, true, true);
          var precoing = get_precoIngrediente(
            ingredientes_itens[tr],
            codtamanho,
            config,
            qtdsabor
          );

          if (precoing !== false) {
            precoing = precoing > 0 ? " R$ " + parseReal(precoing * parseInt(qtd_ingadd[td])) : "";
            htmingreds +=
              "<div class='lst_ings_opc' > <input class='magic-checkbox' type='checkbox' name='layout' data-target-combo='" +
              targetaba +
              "' data-sabor='" +
              codsabor +
              "' data-pedaco='1' id='ing_" +
              valrand_ +
              "' value='" +
              iding +
              "' checked> <label for='ing_" +
              valrand_ +
              "'></label><label class='text nome_ings' style='color: red;' for='ing_" +
              valrand_ +
              "'> + ";
              if(parseInt(qtd_ingadd[td]) > 1) {
                htmingreds += `${qtd_ingadd[td]}x ${nomeingredi}`;
              } else {
                htmingreds += nomeingredi
              }
              htmingreds += precoing +
              " </label></div>";
          }
        }
      }
    }
  }

  $(".ing_modalmont." + targetaba).html(htmingreds);
  $(".ing_modalmont." + targetaba).append("<div class='clear'></div>");
}

function abrirItem(dados, targetaba) {
  var htmcont = "";

  htmcont +=
    "<div class='cont_modalmont' data-combo-confitem='false' data-dadosdoitematual data-dadositem id='" +
    targetaba +
    "'>";

  htmcont +=
    "<div class='esmaecer_montador " +
    targetaba +
    "' style='display:none;'  data-target-combo='" +
    targetaba +
    "'></div>";

  htmcont += reendListaSabores();

  htmcont +=
    "<div class='montador_doitem " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "'>";

  htmcont += "</div>";

  htmcont += "</div>";

  $("#cont_modalmont").html(htmcont);

  peencheDadosRetorno(dados, targetaba);

  var dadosdoitematual = $("#" + targetaba).data("dadosdoitematual");
  var dadositem = $("#" + targetaba).data("dadositem");
  var confitem = $("#" + targetaba).data("combo-confitem");
  var tamanhosposiveis = confitem.tamanhos;

  var opcionaisitem = confitem.opcionais;
  var hash = dadosdoitematual.data_hash;

  var contsabores = parseInt(dadositem.item_qtdsabor);
  var conttamanhositem = tamanhosposiveis.length;
  var dadossessao = get_dadosSessao(dadositem.item_sessaoid);
  var codtamanho = dadositem.item_tamanhoid;

  var per_bordas = getNomeBorda(codtamanho);
  var per_ingred = true;
  var per_obs = getNomeObservacoes(codtamanho);
  var per_massa = getNomeMassa(codtamanho);

  if (contsabores === 1) {
    $(".itensdelistasabores." + targetaba).removeClass("addsabor");

    var htmlmt_1s = htmlMontadorItem_1s(targetaba);
    $(".montador_doitem." + targetaba).html(htmlmt_1s);

    var codsabor = dadositem.sabores[0].item_saborid;
    var nomesabor = dadositem.sabores[0].item_sabornome;

    var ftid = dadositem.sabores[0].item_saborfotoid;
    var ftnome = dadositem.sabores[0].item_saborfotonome;

    // reenderiza lista de tamanhos
    rendTamanhosSelect_(confitem.tamanhos, codtamanho, targetaba);
    // reenderiza lista de ingredientes
    rendIngredientesSabor_1(targetaba, codsabor);
    $(".nometetleitem." + targetaba).text(nomesabor);
    $(".img_modalmont." + targetaba).attr(
      "src",
      "" + urlsfiles.imagens + "produtos/" + ftid + "/240/" + ftnome
    );
    if (conttamanhositem > 1) {
      $(".selecttamitem." + targetaba).show();
    } else {
      $(".selecttamitem." + targetaba).hide();
    }

    var htmbtn_opc = "";
    if (per_ingred === true) {
      htmbtn_opc +=
        "<a title='Adicionar Opcionais' class='btnopc_montmodal " +
        targetaba +
        "' data-target-combo='" +
        targetaba +
        "' data-pdc='1' data-codsabor='" +
        codsabor +
        "'>+ Adicionar Ingredientes</a>";
    }
    if (
      per_bordas !== false &&
      get_bordadasessao(dadossessao.sessao_id, codtamanho) !== false
    ) {
      htmbtn_opc +=
        "<a title='" +
        per_bordas +
        "' class='btnbrd_montmodal " +
        targetaba +
        "' data-codtam='" +
        codtamanho +
        "' data-target-combo='" +
        targetaba +
        "'>Selecionar " +
        per_bordas +
        "</a>";
    }
    if (
      per_massa !== false &&
      get_massasdasessao(dadossessao.sessao_id, codtamanho) !== false
    ) {
      htmbtn_opc +=
        "<a title='" +
        per_massa +
        "' class='btnmss_montmodal " +
        targetaba +
        "' data-codtam='" +
        codtamanho +
        "' data-target-combo='" +
        targetaba +
        "'>Selecionar " +
        per_massa +
        "</a>";
    }
    if (
      per_obs !== false &&
      get_observacoesdasessao(dadossessao.sessao_id, codtamanho) !== false
    ) {
      htmbtn_opc +=
        "<a title='Observações' class='btnobs_montmodal " +
        targetaba +
        "' data-codtam='" +
        codtamanho +
        "' data-target-combo='" +
        targetaba +
        "'>Observações</a>";
    }

    $(".ing_modalmont." + targetaba).after(htmbtn_opc);
  }

  $(".nano").nanoScroller();
}

//tamanho_qtdsabormaxima
function get_qtdmax_sabortTamanho(codtamanho) {
  var cnttamanho = tamahos_itens.length;
  for (var c = 0; c < cnttamanho; c++) {
    if (tamahos_itens[c].tamanho_id == codtamanho) {
      return tamahos_itens[c].tamanho_qtdsabormaxima;
    }
  }
  return 1;
}

function get_sessaoSabor(codsabor) {
  var cntsabores = sabores_itens.length;
  for (var f = 0; f < cntsabores; f++) {
    if (codsabor == sabores_itens[f].sabor_id) {
      return sabores_itens[f].sabor_sessaoid;
    }
  }
  return false;
}

function get_tamanhos_dosabor(codsabor) {
  var arrt = [];
  var cnt = 0;
  var cntsabores = sabores_itens.length;
  for (var f = 0; f < cntsabores; f++) {
    if (codsabor == sabores_itens[f].sabor_id) {
      var tamanhos = sabores_itens[f].sabor_precostamanhos;
      for (var g = 0; g < tamanhos.length; g++) {
        var idtamanho =
          sabores_itens[f].sabor_precostamanhos[g]
            .sabor_precotamanhos_codtamanho;
        var qtdmax = get_qtdmax_sabortTamanho(idtamanho);
        arrt[cnt] = { ID: idtamanho, QTDMAX: qtdmax };
        cnt++;
      }
    }
  }
  return arrt;
}

function openModalItem_editar(targetaba) {
  var htmcont = "";

  htmcont +=
    "<div class='cont_modalmont' data-combo-confitem='false' data-dadosdoitematual data-dadositem id='" +
    targetaba +
    "'>";

  htmcont +=
    "<div class='esmaecer_montador " +
    targetaba +
    "' style='display:none;'  data-target-combo='" +
    targetaba +
    "'></div>";

  htmcont += reendListaSabores([], targetaba, []);

  htmcont +=
    "<div class='montador_doitem " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "'>";

  htmcont += "</div>";

  htmcont += "</div>";

  $("#cont_modalmont").html(htmcont);

  $(".listadesaboresescolher." + targetaba).css("left", "-900px");
  $(".nano").nanoScroller();
}

async function rendAbrirItem(dado, targetaba) {
  var msg = dado;
  const qtd_max_ingred_adicionais = (msg.dados.qtd_max_ingred_adicionais !== undefined && msg.dados.qtd_max_ingred_adicionais !== null) ? parseInt(msg.dados.qtd_max_ingred_adicionais) : 0; 

  const qtd_max_por_ingred_adicionais = (msg.dados.qtd_max_por_ingred_adicionais !== undefined && msg.dados.qtd_max_por_ingred_adicionais !== null) ? parseInt(msg.dados.qtd_max_por_ingred_adicionais) : 1;  

  var dados = dado.dados;
  var htmcont = "";

  let permite_addingredientes =  dados.permite_addingredientes ? dados.permite_addingredientes : 'N';
  let ocultarIngredientes = dados.ocultarIngredientes && dados.ocultarIngredientes == 'S'? true : false;

  if(dados.permite_obsmanual && dados.permite_obsmanual === 'S') {
    permite_obsmanual = 'S';
  } else {
    permite_obsmanual = 'N';
  }

  compositionsItemMontador.compositions = [];
  compositionsItemMontador.add = [];

  htmcont +=
    "<div class='cont_modalmont' data-combo-confitem='false' data-dadosdoitematual data-dadositem id='" +
    targetaba +
    "'>";

  htmcont +=
    "<div class='esmaecer_montador " +
    targetaba +
    "' style='display:none;'  data-target-combo='" +
    targetaba +
    "'></div>";

  htmcont += reendListaSabores([], targetaba, []);

  htmcont +=
    "<div class='montador_doitem " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "'>";

  htmcont += "</div>";

  htmcont += "</div>";

  $("#cont_modalmont").html(htmcont);

  $(".listadesaboresescolher." + targetaba).css("left", "-900px");

  peencheDadosRetorno(msg, targetaba);

  var sabores = dados.dadossabores;
  var tamanhosposiveis = dados.tamanhosprecos;
  var hash = dados.hash;

  var dadosdoitematual = {
    data_hash: null,
    data_sabor: [],
    data_tamanho: null,
    data_qtdsabor: null,
    qtd_max_ingred_adicionais: qtd_max_ingred_adicionais,
    qtd_max_por_ingred_adicionais: qtd_max_por_ingred_adicionais
  };
  dadosdoitematual.data_hash = hash;

  var contsabores = sabores.length;
  var conttamanhositem = tamanhosposiveis.length;

  dadosdoitematual.data_qtdsabor = contsabores;

  if (contsabores === 1) {
    var codsabor = sabores[0].sabor_id;
    var nomesabor = sabores[0].sabor_nome;
    var codtamanho = dados.tamanho;
    var codmsspdr = dados.massa;
    var precosabor = get_precosTamanho(dados.tamanhosprecos, codtamanho);
    var ftid = sabores[0].sabor_fotoid;
    var ftnome = sabores[0].sabor_fotonome;
    var sessao = get_sessaoSabor(codsabor);
    var dadossessao = get_dadosSessao(sessao);
    var tamanhos = get_tamanhos_dosabor(codsabor);
    var per_bordas = getNomeBorda(codtamanho);
    var per_ingred = true;
    var per_obs = getNomeObservacoes(codtamanho);
    var per_massa = getNomeMassa(codtamanho);
    item_tamanho = codtamanho;
    let catCompositions = await getCatCompositionsBySessionAndSize(sabores[0]['sabor_sessaoid'], codtamanho);

    per_ingred = permite_addingredientes == 'S' ? true : false;
    per_ingred = ocultarIngredientes ? false : per_ingred;

    dadosdoitematual.data_sabor = [codsabor];
    dadosdoitematual.data_tamanho = codtamanho;

    var htmlmt_1s = htmlMontadorItem_1s(targetaba);
    $(".montador_doitem." + targetaba).html(htmlmt_1s);

    $(".tit_modalmont").text(dadossessao.sessao_nome);
    $(".itensdelistasabores." + targetaba).removeClass("addsabor");
    $(".precotitleitem." + targetaba).text(" - R$ " + parseReal(precosabor));
    $(".precotitleitem." + targetaba).data('price', precosabor);
    await updateValuesCompositionsTotalOrderDesktop();

    // reenderiza lista de tamanhos
    rendTamanhosSelect_(tamanhos, codtamanho, targetaba);
    // reenderiza lista de ingredientes
    rendIngredientesSabor_1(targetaba, codsabor);
    $(".nometetleitem." + targetaba).text(nomesabor);
    $(".img_modalmont." + targetaba).attr(
      "src",
      "" + urlsfiles.imagens + "produtos/" + ftid + "/240/" + ftnome
    );
    if (conttamanhositem > 1) {
      $(".selecttamitem." + targetaba).show();
    } else {
      $(".selecttamitem." + targetaba).hide();
    }

    var htmbtn_opc = "";
    if (per_ingred === true) {
      htmbtn_opc +=
        "<a title='Adicionar Opcionais' class='btnopc_montmodal " +
        targetaba +
        "' data-target-combo='" +
        targetaba +
        "' data-pdc='1' data-codsabor='" +
        codsabor +
        "'>+ Adicionar Ingredientes</a>";
    }
    if (
      per_bordas !== false &&
      get_bordadasessao(dadossessao.sessao_id, codtamanho) !== false
    ) {
      htmbtn_opc +=
        "<a title='" +
        per_bordas +
        "' class='btnbrd_montmodal " +
        targetaba +
        "' data-codtam='" +
        codtamanho +
        "' data-target-combo='" +
        targetaba +
        "'>Selecionar " +
        per_bordas +
        "</a>";
    }
    if (
      per_massa !== false &&
      get_massasdasessao(dadossessao.sessao_id, codtamanho) !== false
    ) {
      htmbtn_opc +=
        "<a title='" +
        per_massa +
        "' class='btnmss_montmodal " +
        targetaba +
        "' data-codmsspdr='" +
        codmsspdr +
        "' data-codtam='" +
        codtamanho +
        "' data-target-combo='" +
        targetaba +
        "'>Selecionar " +
        per_massa +
        "</a>";
    }

    if (catCompositions) {
      for (let i = 0; i < catCompositions.length; i++) {
        htmbtn_opc += `<a title='${catCompositions[i]['NOME']}' data-catcompositionid='${catCompositions[i]['ID']}' class='btncomposicao_montmodal ${targetaba}' data-codtam='${codtamanho}' data-target-combo='${targetaba}'>${catCompositions[i]['NOME']}</a>`;
      }
    }

    if (
      per_obs !== false &&
      get_observacoesdasessao(dadossessao.sessao_id, codtamanho) !== false
    ) {
      htmbtn_opc +=
        "<a title='Observações' class='btnobs_montmodal " +
        targetaba +
        "' data-codtam='" +
        codtamanho +
        "' data-target-combo='" +
        targetaba +
        "'>Observações</a>";
    }

    $(".ing_modalmont." + targetaba).after(htmbtn_opc);
  }
  $("#" + targetaba).data("dadosdoitematual", dadosdoitematual);

  var htmlqtd =
    "<p>Quantidade:</p>" +
    "<div class='qtd_modalcont'>" +
    "<a href='#' title='Remover' class='menosum_item " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' >-</a>" +
    "<input type='text' value='01' readonly='true'></input>" +
    "<a href='#' title='Adicionar' class='maisum_item " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' >+</a>" +
    "<div class='clear'></div>" +
    "</div>";
  $(".img_modalmont." + targetaba).after(htmlqtd);

  if(permite_obsmanual === 'S') {
    let input_observacao = `
      <textarea rows="3" id="obspedido" class="obs_item" placeholder="Alguma observação?" style="width: 80%;margin-top: 15px;" maxlength="140"></textarea>
    `;
    $(".coluna_direita." + targetaba).append(input_observacao);
  }
  
  var html_btncomprar =
    " <div class='clear'></div><a title='Adicionar ao carrinho' id='btncomprar_montmodal' class='comprar_item " +
    targetaba +
    "'  data-target-combo='" +
    targetaba +
    "' ><span class='icon-comprarmodal'></span>Comprar!</a> ";
  $(".coluna_direita." + targetaba).append(html_btncomprar);

  $(".nano").nanoScroller();
  
  if (dado.dados.qtdSabores != undefined && dado.dados.qtdSabores > 1) {
    //Abre montador com qtd de sabores padrão do tamanho selecionada
    $('.selectqtditem').val(dado.dados.qtdSabores).change();
  }
}

function get_precosTamanho(lista, tamanho) {
  var precoret = lista[0].tamanho_preco;
  var cntlista = lista.length;
  for (var i = 0; i < cntlista; i++) {
    if (tamanho == lista[i].tamanho_id) {
      precoret = lista[i].tamanho_preco;
    }
  }
  return precoret;
}

function rendPizzaMontagem(dados) {
  var nomemontador = dados.montador;

  var tgtcb = dados.targetcombo;
  var contSab = dados.sabor.length;
  var sabor = dados.sabor;

  var imgforma = "forma";
  var cssquadrada = "";
  var cssformadapizza = "";
  var csstresmeio = "";
  var csstaboameio = "";
  if (nomemontador == "montarpizzaquadrada") {
    imgforma = "formaquadrada";
    cssquadrada =
      'style="background-repeat: no-repeat;background-position: 57px 62px;" ';
    cssformadapizza =
      ' style="-webkit-border-radius: initial !important; -moz-border-radius: initial !important; border-radius: initial !important;" ';
    csstresmeio =
      ' style=" right: 12%; width: 75%; height: 75%; top: -41.8%; border-top-left-radius:initial !important;" ';
    csstaboameio =
      'style="background: url(' +
      urlsfiles.media +
      vsao +
      '/img/formaquadrada_meio.png) no-repeat; background-position: 46px 47px;" ';
  }

  var htmpz = '<div class="areapizza ' + tgtcb + '" ' + cssformadapizza + ">";
  var htmpzX = "";
  if (dados.qtdsabor == 1) {
    //htmpzX += '<span class="icones removesabor umsabor '+tgtcb+'" data-target-combo="'+tgtcb+'" data-idsabor=""  data-pedaco="1" style="display: none;" title="Remover sabor"></span>';
    htmpz +=
      '<div class="pztop-abs pzinteira"  style="background-position: top left;">' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-tamanhopizza="' +
      dados.tamanho +
      '" data-pedaco="1" data-pdc="1" data-qtdsabores="1"></span>' +
      "</div>";
    $(".formapizza." + tgtcb).css({
      "background-image":
        "url(" + urlsfiles.media + vsao + "/img/" + imgforma + "_1.png)",
    });
  } else if (dados.qtdsabor == 2) {
    //htmpzX += '<span class="icones removesabor doissabores-esq '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="1" style="display: none;" title="Remover sabor"></span>'
    //        + '<span class="icones removesabor doissabores-dir '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="2" style="display: none;" title="Remover sabor"></span>';
    htmpz +=
      '<div class="pztop-abs metade_esq"  style="background-position: top left;">' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-tamanhopizza="' +
      dados.tamanho +
      '" data-pedaco="1" data-pdc="1" data-qtdsabores="2"></span>' +
      "</div>";
    htmpz +=
      '<div class="pztop-abs metade_dir"  style="background-position: top right;">' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-tamanhopizza="' +
      dados.tamanho +
      '" data-pedaco="2" data-pdc="2" data-qtdsabores="2"></span>' +
      "</div>";
    $(".formapizza." + tgtcb).css({
      "background-image":
        "url(" + urlsfiles.media + vsao + "/img/" + imgforma + "_2.png)",
    });
  } else if (dados.qtdsabor == 3) {
    //htmpzX += '<span class="icones removesabor tressabores-esq '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="1" style="display: none;" title="Remover sabor"></span>'
    //    + '<span class="icones removesabor tressabores-meio '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="2" style="display: none;" title="Remover sabor"></span>'
    //    + '<span class="icones removesabor tressabores-dir '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="3" style="display: none;" title="Remover sabor"></span>';
    htmpz +=
      '<div class="pztop-abs tres_esq" > ' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-pedaco="1" data-pdc="1" data-tamanhopizza="' +
      dados.tamanho +
      '" data-qtdsabores="3"></span>' +
      "</div>";
    htmpz +=
      '<div class="pztop-abs tres_dir"  style="background-position: right bottom;" >' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-pedaco="3" data-pdc="3" data-tamanhopizza="' +
      dados.tamanho +
      '" data-qtdsabores="3"></span>' +
      "</div>";
    htmpz +=
      '<div class="pztop-abs tres_meio" ' +
      csstresmeio +
      " >" +
      '<div class="bgtaboa" ' +
      csstaboameio +
      "></div>" +
      '<span class="fotosabmeio ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" ' +
      cssquadrada +
      " >" +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-pedaco="2" data-pdc="2" data-tamanhopizza="' +
      dados.tamanho +
      '" data-qtdsabores="3"></span>' +
      "</span>" +
      "</div>";
    $(".formapizza." + tgtcb).css({
      "background-image":
        "url(" + urlsfiles.media + vsao + "/img/" + imgforma + "_3.png)",
    });
  } else if (dados.qtdsabor == 4) {
    //htmpzX += '<span class="icones removesabor quatrosab-top-esq '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="1" style="display: none;" title="Remover sabor"></span>'
    //    + '<span class="icones removesabor quatrosab-top-dir '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="2" style="display: none;" title="Remover sabor"></span>'
    //    + '<span class="icones removesabor quatrosab-bott-esq '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="3" style="display: none;" title="Remover sabor"></span>'
    //    + '<span class="icones removesabor quatrosab-bott-dir '+tgtcb+'" data-target-combo="'+tgtcb+'" data-pedaco="4" style="display: none;" title="Remover sabor"></span>';
    htmpz +=
      '<div class="pztop-abs quarto_esq_cima" style="background-position: top left;">' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-tamanhopizza="' +
      dados.tamanho +
      '" data-pedaco="1" data-pdc="1" data-qtdsabores="4"></span>' +
      "</div>" +
      '<div class="pztop-abs quarto_dir_cima" style="background-position: top right;">' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-tamanhopizza="' +
      dados.tamanho +
      '" data-pedaco="2" data-pdc="2" data-qtdsabores="4"></span>' +
      "</div>" +
      '<div class="quarto_esq_baixo" style="background-position: bottom left;">' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-tamanhopizza="' +
      dados.tamanho +
      '" data-pedaco="3" data-pdc="3" data-qtdsabores="4"></span>' +
      "</div>" +
      '<div class="quarto_dir_baixo" style="background-position: bottom right;">' +
      '<span class="linkpizza openlistasabores ' +
      tgtcb +
      '" data-target-combo="' +
      tgtcb +
      '" data-idsabor="0" data-tamanhopizza="' +
      dados.tamanho +
      '" data-pedaco="4" data-pdc="4" data-qtdsabores="4"></span>' +
      "</div>";
    $(".formapizza." + tgtcb).css({
      "background-image":
        "url(" + urlsfiles.media + vsao + "/img/" + imgforma + "_4.png)",
    });
  }
  htmpz += "</div>";
  htmpz = htmpzX + htmpz;
  $(".formapizza." + tgtcb).html(htmpz);

  for (var sb = 0; sb < contSab; sb++) {
    var ped = sabor[sb].pedaco;
    var idsabp = sabor[sb].codsabor;
    var nomesabor = sabor[sb].nome;
    var foto = sabor[sb].urlfoto;

    if ($("." + tgtcb + ".linkpizza[data-pedaco='" + ped + "']").length === 1) {
      $("." + tgtcb + ".icones.removesabor[data-pedaco='" + ped + "'] ").css(
        "display",
        "inline"
      );
      $("." + tgtcb + ".icones.removesabor[data-pedaco='" + ped + "'] ").data(
        "idsabor",
        idsabp
      );

      var pedpz = $("." + tgtcb + ".linkpizza[data-pedaco='" + ped + "']");

      pedpz.data("idsabor", idsabp);
      pedpz.attr("title", nomesabor);

      var bgped = pedpz.parent();

      if (foto !== null) {
        bgped.css({ "background-image": "url(" + foto + ")" });
      }
    }
  }
}

function addIngAddQtdMontadorPizza(e){
  let cod_ing = $(e.target).data('id_ing');
  const dadositemmontando = $("#cont_mont_lanche").data("dadosdoitematual");
  let codsabor = $(e.target).data("sabor");
  let pedaco = $(e.target).data("pedaco");
  let element_qtd = $(`.qtd_txt[data-id_ing="${cod_ing}"]`);
  let qtd_atual = element_qtd.html();
  let qtd_max = $(e.target).data('qtd_max');
  qtd_atual = parseInt(qtd_atual);
  qtd_max = parseInt(qtd_max);

  const infTamanhoSelecionado = $('#sel-tamanho').data('ddslick');
  let qtd_max_ingred_adic = infTamanhoSelecionado.selectedData.qtd_max_ingred_adicionais
  if (qtd_max_ingred_adic === null || qtd_max_ingred_adic === undefined) {
      qtd_max_ingred_adic = infTamanhoSelecionado.qtd_max_ingred_adicionais;
  }

  let total_ingred_add = 0;

  $('.qtd_txt').each(function(e){
      let qtd = $(this).html();
      qtd = parseInt(qtd);
      total_ingred_add = total_ingred_add + qtd;
  });

  if(qtd_max_ingred_adic > 0 && total_ingred_add >= qtd_max_ingred_adic) {
  Swal({
      type: "warning",
      title: "Quantidade Inválida",
      html: `Não é possível adicionar mais que ${qtd_max_ingred_adic} ingredientes para este tamanho!`
  }); 
  return;
  }

  if(qtd_max > 0 && qtd_atual >= qtd_max) {
  Swal({
      type: "warning",
      title: "Quantidade Inválida",
      html: `Não é possível adicionar mais que ${qtd_max} de cada ingrediente!`
  }); 
  return;
  }
  let qtd_nova = parseInt(qtd_atual) + 1;
  element_qtd.html(qtd_nova);
  let acao = 'add_qtd_ing';

  let dadosAcao = {
      insumo: cod_ing,
      sabor: codsabor,
      pedaco: pedaco,
  };
  acoesInsumos(dadositemmontando, dadosAcao, acao, undefined, qtd_nova);
};

function removeIngAddQtdMontadorPizza(e){
  let cod_ing = $(e.target).data('id_ing');
  const dadositemmontando = $("#cont_mont_lanche").data("dadosdoitematual");
  let codsabor = $(e.target).data("sabor");
  let pedaco = $(e.target).data("pedaco");
  let element_qtd = $(`.qtd_txt[data-id_ing="${cod_ing}"]`);
  let qtd_atual = element_qtd.html();
  qtd_atual = parseInt(qtd_atual);
  if(qtd_atual <= 0) return;
  let qtd_nova = parseInt(qtd_atual) - 1;
  element_qtd.html(qtd_nova);
  let acao = 'remove_qtd_ing';

  let dadosAcao = {
      insumo: cod_ing,
      sabor: codsabor,
      pedaco: pedaco,
  };
  acoesInsumos(dadositemmontando, dadosAcao, acao, undefined, qtd_nova);
};

function setCompositionsItemCombo(comboItemHash, target, resetCompositions = false){
  return new Promise(async (resolve, reject) => {
    const checkCompositions = await checkItemCompositions();
    if (!checkCompositions) {
      resolve(false);
      return;
    }
  
    const checkCompositionsAdd = await checkItemCompositions('Add');
    if (!checkCompositionsAdd) {
      resolve(false);
      return;
    }

    let compositions = await getCompositionsItem();
    let compositionsAdd = await getCompositionsItem('Add');

    if (!compositions || compositions.length < 1) {
      resolve(true);
      return;
    }

    $('.loading').show();
    let ajaxCompositions = $.ajax({
      url: "/exec/montadoritem/setcomposicoesitemcombo/",
      method: "POST",
      data: {
        comboItemHash,
        compositions,
        compositionsAdd
      },
      dataType: "json",
      statusCode: {
          404: function() {
              $('.loading').hide();
              Swal({
                  title: "Ops! Algo deu Errado",
                  html: "Sem conexão com a internet.\nTente novamente mais tarde.",
                  type: "error",
              }); 
              resolve(false);
              return;
          },
          500: function() {
              $('.loading').hide();
              Swal({
                  title: "Ops! Algo deu Errado",
                  html: "Ocorreu um erro.\n Tente novamente mais tarde.",
                  type: "error",
              });
              resolve(false);
              return;
          }
      }
    });
  
    ajaxCompositions.done(function(msg){
      if (msg.res){
        let dataItem = $("#" + target).data("dadositem");
        if (dataItem && (dataItem.length > 0 || typeof dataItem == 'object')) {
          dataItem['item_compositions'] = compositions;
          dataItem['item_compositionsAdd'] = compositionsAdd;
          $("#" + target).data("dadositem", dataItem);
        }
        if (resetCompositions) resetArrayCompositionsItem()
        resolve(true);
        return;
      }
      Swal({
          title: "Ops! Algo deu Errado",
          html: msg.msg,
          type: "error"
      });
      resolve(false);
    });
  
    ajaxCompositions.fail(function( jqXHR, textStatus ) {
      $('.loading').hide();
      Swal({
          title: "Ops! Algo deu Errado",
          text: "Tente novamente.",
          type: "error"
      }); 
      resolve(false);
      return;
    }); 
  });
}
