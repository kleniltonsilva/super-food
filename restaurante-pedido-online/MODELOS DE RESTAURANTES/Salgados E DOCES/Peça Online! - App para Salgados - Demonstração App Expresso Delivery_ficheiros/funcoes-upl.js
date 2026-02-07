$(document).ready(function(){
    /*
     * 
     <a href="#" title="Editar antes de adicionar ao pedido" data-coditem="14" data-codtamanho="11" data-codtipodoitem="6" class="btn-ter-item btn-editar-item"></a>
     */
    /*$(document).on("click",".lblopt,.lbldescopt",function(e){
        popMassa();
        showModalMassa();
    });*/
    
    $(document).on("click",".selectbrd",function(e){
        var fdka = $(this).data("codbrd");
        add_borda(fdka,"massa");
    });
    
    $(document).on("click",".link-sel-borda", function(e){
        showModalBordamaisq4();
    });
    
    $(document).on("click",".selectmassa",function(e){
        var cod = $(this).data("codmassa");
        add_borda(cod,"massa");
    });
    $(document).on("click",".closethismodal",function(e){
        fechaModalUniv();
    });
    
    
    /*
    $(document).on("click",".btn-editar-item",function(e){
        var codtam = $(this).data("codtamanho");
        var codtipo = $(this).data("codtipodoitem");
        var coditem = $(this).data("coditem");
        $.ajax({
            method: "POST",
            url: "/exec/pedido/add_newitemp/?hashsss="+identsss,
            data: {coditem: coditem, codtipo: codtipo, codtam : codtam},
            dataType: "json"
        }).done(function( msg ) {
            if(msg.res === true){
                if(msg.redir != false){
                    document.location.href = msg.redir;
                }else{
                    pizzaatual = msg.pizza;
                    if(isimples !== true){
                        resetMontadorPizza();
                        rendPizzaMontagem(msg.pizza);
                        rendPlugnsMontagem(msg.pizza);
                        //rendIngredBox(coditem,1);
                    }else{
                        rendSimplaMontagem(msg.pizza);
                        rendIngredBox(coditem,1);
                    }
                    
                    Ancora("resumo-pizza");
                    resumoitenspedd = msg.resumo;
                    rendResumo(msg.resumo);
                    //animasaoadditem();
                }
            }else if(msg.res === false){
                alert("erro");
            }
        });
        
    });
    */
   
   /*
    $(document).on("click",".btn-comprar-item",function(e){
        var codtam = $(this).data("codtamanho");
        var codtipo = $(this).data("codtipodoitem");
        var coditem = $(this).data("coditem");
        $.ajax({
            method: "POST",
            url: "/exec/pedido/add_newitempedido/?hashsss="+identsss,
            data: {coditem: coditem, codtipo: codtipo, codtam : codtam},
            dataType: "json"
        }).done(function( msg ) {
            if(msg.res === true){                    
                resumoitenspedd = msg.resumo;
                rendResumo(msg.resumo);     
                animasaoadditem();
            }else if(msg.res === false){
                alert("erro");
            }
        });
    });
    
    */
    
    /*
    $(document).on("click",".btn-comprar-itemso",function(e){
        var codtam = $(this).data("codtamanho");
        var codtipo = $(this).data("codtipodoitem");
        var coditem = $(this).data("coditem");
        $.ajax({
            method: "POST",
            url: "/exec/pedido/add_newitempedido/?hashsss="+identsss,
            data: {coditem: coditem, codtipo: codtipo, codtam : codtam},
            dataType: "json"
        }).done(function( msg ) {
            if(msg.res === true){                    
                resumoitenspedd = msg.resumo;
                rendResumo(msg.resumo);   
                animasaoadditem();
            }else if(msg.res === false){
                alert("erro");
            }
        });
    });
    */
    
    /*
    setTimeout(function(){
        if($(".linksess.linksess_0").length > 0){
            $(".linksess.linksess_0").trigger("click");
        }
    },200);
    
    setTimeout(function(){
        if($(".abas_tamitem.ascats_0").length > 0){
            //$(".abas_tamitem.ascats_0").trigger("click");
            $(".abas_tamitem.ascats_0").each(function() {
                $( this ).trigger("click");
            });
        }
    },800);    
    
    setTimeout(function(){
        $(".selectam").change();
    },600);
    
    $(document).on("click", ".linksess", function(e){
        var cdsess = $(this).data("codsess");
        $(".item_e").hide();
        $("#item_e"+cdsess).show();
        $(".linksess").parent().removeClass("ativo");
        $(this).parent().addClass("ativo");
    });
    $(document).on("change",".selectam",function(e){
        var tamcdsess = $(this).data("tamcodsessao");
        var tamcod = $(this).val();
        //$(".abas_tamitem[data-tamcodsessao='"+tamcdsess+"']").removeClass("activetans");
        //$(this).addClass("activetans");
        var codcat = $(".activetans").data("codcat");
        
        $(".tamsessao_"+tamcdsess).hide();
        $(".tamanho_cd"+tamcod+".categoria_cd"+codcat).show();
        $(".abas_tamitem.activetans").trigger("click");
    });
    
    $(document).on("click",".abas_tamitem",function(e){
        var tamcdsess = $(this).data("tamcodsessao");
        var tamcod = $(this).data("codcat");
        var codtam = $("#selectam"+tamcdsess).val();
        $(".abas_tamitem[data-tamcodsessao='"+tamcdsess+"']").removeClass("activetans");
        $(this).addClass("activetans");
        //console.log("categoria "+tamcod);
        $(".tamsessao_"+tamcdsess).hide();
        if(codtam != undefined){
            //console.log("tamanho e categoria");
            $(".tamsessao_"+tamcdsess+".categoria_cd"+tamcod+".tamanho_cd"+codtam).show();
        }else{
            //console.log("so categoria");
            $(".tamsessao_"+tamcdsess+".categoria_cd"+tamcod).show();
        }
    });
    */
    
    $(document).on("click",".selectpizzabroto",function(e){
        var coditem = $(this).data("codpizza");
        additemppromo(coditem,"pizza");
    });
    
    $(document).on("click",".selectrefrigr",function(e){
        var coditem = $(this).data("codrefri");
        additemppromo(coditem,"refri");
    });
    
    
});

function animasaoadditem(){
    
    $(".itemaddcionado").show();
    ////console.log("animate");
    setTimeout(function(){
        $('.itemaddcionado').hide();
    }, 1800);
    
}

function additemppromo(coditem,tipo){
    
    
    $.ajax({
        method: "POST",
        url: "/exec/pedido/additemgratis/?hashsss="+identsss,
        data: {codbbd: coditem, tipo: tipo},
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){
            resumoitenspedd = msg.resumo;
            rendResumo(msg.resumo);
        }else if(msg.res === false){
            alert("erro");
        }
        fechaModalUniv();
    });
    
}


function showModalItemRefri(){
	
    $.pgwModal({
        target: '#modalRefri',
        //title: 'Qual o Tamanho?',
        closable: false,
        titleBar: false,
        maxWidth: 460
    });
    $(".pm-content").css("padding","0px");
}


function showMontadorUniver(){
    
    
    $.pgwModal({
        target: '#modalmontador',
        //title: 'Qual o Tamanho?',
        closable: false,
        titleBar: false,
        maxWidth: 910
    });
    $(".pm-content").css("padding","0px");
}

function showModalItemPizza(){
	
    $.pgwModal({
        target: '#modalPizza',
        //title: 'Qual o Tamanho?',
        closable: false,
        titleBar: false,
        maxWidth: 460
    });
    $(".pm-content").css("padding","0px");
}




function showModalMassa(){
	
    $.pgwModal({
        target: '#modalMassa',
        //title: 'Qual o Tamanho?',
        //closable: false,
        titleBar: false,
        maxWidth: 460
    });
    $(".pm-content").css("padding","0px");
}


/*** Função Add Animação via jQUery - Executa animação apenas 1 vez ***/
$.fn.extend({
    animateCss: function (animationName) {
        var animationEnd = 'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend';
        $(this).addClass('animated ' + animationName).one(animationEnd, function() {
            $(this).removeClass('animated ' + animationName);
        });
    }
});


/** Balao orientação**/

function subir(par){
    $('#maozinha').animate({bottom: '-=10'}, 400, function() {
        if(efeitomaozinha===true){
            par(subir);
        }
    });
}
function descer(parx){
    $('#maozinha').animate({bottom: '+=10'}, 400, function() {
        if(efeitomaozinha===true){
            parx(descer);
        }
    });
}

function showModalBordamaisq4(){
    $.pgwModal({
        target: '#modalBordamaisq4',
        //title: 'Qual o Tamanho?',
        //closable: false,
        titleBar: false,
        maxWidth: 460
    });
    $(".pm-content").css("padding","0px");
}

function modalItensGratis(){
    rendVCitens(pizzaatual);
    
    $.pgwModal({
        target: '#listaitensgratis',
        //title: 'Qual o Tamanho?',
        //closable: false,
        titleBar: false,
        maxWidth: 460
    });
    $(".pm-content").css("padding","0px");
}

function showModalAddEndereco(){
	$("#ModalNovoEndereco").modal("show");
	/*
    $.pgwModal({
        target: '#ModalNovoEndereco',
        //title: 'Cadastrar novo endereço',
        closable: false,
        titleBar: false,
        maxWidth: 800
    });
    $(".pm-content").css("padding","0px");*/
}


function showModalEscolhafilial(){
    $.pgwModal({
        target: '#modalEscolhaFilial',
        titleBar: false,
        maxWidth: 780
    });
    $(".pm-content").css("padding","0px");
}

function showModalAreasAtendidas(){
  $('#modalAreasAtendidas').show();
  if (!render_mapa_raio) {
      //configurações e funções do raio no mapa
      render_mapa_raio = L.map('map').setView([filial_latitude, filial_longitude], 12);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '© OpenStreetMap'
      }).addTo(render_mapa_raio);
      
      L.marker([filial_latitude, filial_longitude]).addTo(render_mapa_raio);

      if (maiorRaioAlcance_entrega) {
          for (let km = 1; km <= maiorRaioAlcance_entrega; km++) {
            L.circle([filial_latitude, filial_longitude], {radius: `${km}000`}).addTo(render_mapa_raio).setStyle({color: 'green', weight: 2, dashArray: "4", fill: false});
          }
      }

      if (areaExclusao_entrega) { 
        areaExclusao_entrega['features'].forEach(function(area) {
          area['geometry'] = area['geometry']['geometry'] ? area['geometry']['geometry'] : area['geometry'];
          L.geoJSON(area, {color: "red"}).addTo(render_mapa_raio);
        });
      }

      let menu_mapa_taxas = null;

      if (raios_entregaArray.length > 0) {
        let html_raiosTaxas = "";
        for (let i = 0; i < raios_entregaArray.length; i++) {
          html_raiosTaxas += `
            <div>
              <span>🛵 Até ${raios_entregaArray[i].RAIO} KM</span>
              <span>R$ ${parseReal(raios_entregaArray[i].TAXA_ENTREGA)}</span>
            </div>
          `;
        }

        menu_mapa_taxas = L.control({ position: 'topleft' });
        menu_mapa_taxas.onAdd = function (map) {
            this._div = L.DomUtil.create('div', 'menu_mapa_taxas');
            this._div.innerHTML = `
                <div class="div_taxas">
                  <div class="title_raios">Taxas de Entrega</div>
                  <div class="body_raios">
                      ${html_raiosTaxas}
                  </div>
                </div>
            `;
            return this._div;
        };
  
        menu_mapa_taxas.addTo(render_mapa_raio);
      }

  }
}

function formatarParaReal(mixed) {
    var int = mixed.toFixed(2).toString().replace(/[^\d]+/g, '');
    var tmp = int + '';
    tmp = tmp.replace(/([0-9]{2})$/g, ",$1");
    //if (tmp.length > 6)
    //tmp = tmp.replace(/([0-9]{3}),([0-9]{2}$)/g, "$1,$2");
    tmp = tmp.replace(/\D/g, "");// Remove tudo o que não é dígito
    //tmp = tmp.replace(/(\d{2})(\d)/, "$1,$2");
    return tmp;
}

function abrir_box(id) {
    var maskHeight = $(document).height();
    var maskWidth = $(window).width();

    $('#mask').css({'width': maskWidth, 'height': maskHeight});

    //$('#mask').fadeIn(500);	
    $('#mask').fadeTo("slow", 0.6);

    //Get the window height and width
    var winH = $(window).height();
    var winW = $(window).width();

    //centraliza div
    $(id).css('top', winH / 2 - $(id).height() / 2);
    $(id).css('left', winW / 2 - $(id).width() / 2);

    //efeito transição
    $(id).stop().fadeIn(1000);
}

function abrir_aviso(id) {
    var maskHeight = $(document).height();
    var maskWidth = $(window).width();

    $('#maskx').css({'width': maskWidth, 'height': maskHeight});

    //$('#mask').fadeIn(500);	
    $('#maskx').fadeTo("slow", 0.6);

    //Get the window height and width
    var winH = $(window).height();
    var winW = $(window).width();

    //centraliza div
    $(id).css('top', winH / 2 - $(id).height() / 2);
    $(id).css('left', winW / 2 - $(id).width() / 2);

    //efeito transição
    $(id).fadeIn(1000);
}

function editarPizzaPedido(coditem, skeyitm, seg, elen){
    $.ajax({
           method: "POST",
           url: "/exec/pedido/editar_item/?hashsss="+identsss,
           data: {coditem: coditem, skeyitm : skeyitm, seg : seg },
           dataType: "json"
   }).done(function( msg ) {
       if(msg.res === true){
            resumoitenspedd = msg.resumo;
            pizzaatual = msg.pizza;
            
            if(msg.redir !== false){
                document.location.href = msg.redir;
            }else{
                resetMontadorPizza();                    
                elen.remove();
                if(resumoitenspedd.desconto > 0){
                    $("#sub_desc").show();
                    $(".subTotaoped").text("Subtotal R$ "+parseReal(resumoitenspedd.subtotal));
                    $(".descontoTotalped").text("Desconto R$ "+parseReal(resumoitenspedd.desconto));
                    $("#txttotal").addClass("totalverde");
                    $("#txttotal").css("margin-bottom","0px");
                }else{
                    $("#txttotal").css("margin-bottom","15px");
                    $("#txttotal").removeClass("totalverde");
                    $("#sub_desc").hide();
                }
                $("#totalrs-ped").text(parseReal(resumoitenspedd.valortotal));
                atualizaMiniResumo();
                //$("#desconto-ped").text(parseReal(resumoitenspedd.desconto));
                //resumo-pizza
                Ancora("resumo-pizza");
            }
       }else if(msg.res === false){
           /*if(pgacss !== 0){
               document.location.href = "/teste/index.php";
           }*/
           resumoitenspedd = msg.resumo;
           rendResumo(resumoitenspedd);
       }else{
           
       }
   });        
}

function removeItemPedido(coditem, skeyitm, seg,elen){
    $.ajax({
           method:"POST",
           url:"/exec/pedido/add_remove_item/?hashsss="+identsss,
           data: {coditem: coditem, skeyitm : skeyitm, seg : seg, acao : "remov"  },
           dataType: "json"
   }).done(function( msg ) {
       if(msg.res === true){
           resumoitenspedd = msg.resumo;
           elen.remove();
           rendResumo(resumoitenspedd);
           /*
           if(resumoitenspedd.desconto > 0){
                $("#sub_desc").show();
                $(".subTotaoped").text("Subtotal R$ "+parseReal(resumoitenspedd.subtotal));
                $(".descontoTotalped").text("Desconto R$ "+parseReal(resumoitenspedd.desconto));
                $("#txttotal").addClass("totalverde");
                $("#txttotal").css("margin-bottom","0px");
            }else{
                $("#txttotal").css("margin-bottom","15px");
                $("#txttotal").removeClass("totalverde");
                $("#sub_desc").hide();
            }
           $("#totalrs-ped").text(parseReal(resumoitenspedd.valortotal));*/
           atualizaMiniResumo();
           //$("#desconto-ped").text(parseReal(resumoitenspedd.desconto));
       }else if(msg.res === false){
           resumoitenspedd = msg.resumo;
           rendResumo(resumoitenspedd);
       }else{
           
       }
   });
}

function addMaisMenosItem(coditem, skeyitm, seg, acao,elen){
    $.ajax({
           method:"POST",
           url:"/exec/pedido/add_remove_item/?hashsss="+identsss,
           data: {coditem: coditem, skeyitm : skeyitm, seg : seg, acao : acao  },
           dataType: "json"
   }).done(function( msg ) {
       if(msg.res === true){
           resumoitenspedd = msg.resumo;
           elen.val(msg.qtdd);
           rendResumo(resumoitenspedd);
           /*if(resumoitenspedd.desconto > 0){
                $("#sub_desc").show();
                $(".subTotaoped").text("Subtotal R$ "+parseReal(resumoitenspedd.subtotal));
                $(".descontoTotalped").text("Desconto R$ "+parseReal(resumoitenspedd.desconto));
                $("#txttotal").addClass("totalverde");
                $("#txttotal").css("margin-bottom","0px");
            }else{
                $("#txttotal").css("margin-bottom","15px");
                $("#txttotal").removeClass("totalverde");
                $("#sub_desc").hide();
            }*/
           $("#totalrs-ped").text(parseReal(resumoitenspedd.valortotal));
           atualizaMiniResumo();
            
           //$("#desconto-ped").text(parseReal(resumoitenspedd.desconto));
       }else if(msg.res === false){
           resumoitenspedd = msg.resumo;
           rendResumo(resumoitenspedd);
       }else{
           
       }
   });        
}

function atualizaMiniResumo(){
    var resumo = resumoitenspedd;
    
    var contBebida = resumo.bebidas.length;
    var contPizza = resumo.pizzas.length;
    
    
    var qtddtotal = 0;
    if(contPizza > 0){
        for( var p = 0; p < contPizza; p++){
            var qtddpzz = resumo.pizzas[p].qttdd;
            qtddtotal += parseInt(qtddpzz);
            if(resumo.pizzas[p].itemvc.nome_item !== undefined){
                qtddtotal += parseInt(qtddpzz);
            }
        }
    }
    
    if(contBebida > 0){
        for( var b=0; b<contBebida; b++){
            qtddtotal += parseInt(resumo.bebidas[b].qtdd);
        }
    }
    
    
    var totalcompra = parseReal(resumo.valortotal);
    
    if(qtddtotal == 0){                
        var htmResumo = "<div class='car-sem-item'> <img src='"+urlsfiles.media+vsao+"/img/emot-fome.png' /> <img style='margin-top: 50px;' src='"+urlsfiles.media+vsao+"/img/seta-add-item.png' /> </div> ";
        $("#allitens").html(htmResumo);
        $("#total-finaliza-ped").hide();
    }else{
        $("#total-finaliza-ped").show();
    }
        
    if(qtddtotal > 1){
        $("#qtd-miniresumo").text(qtddtotal + " itens");
        $("#valor-miniresumo").text( "R$ " + totalcompra);
    }else if(qtddtotal == 1){
        $("#qtd-miniresumo").text("1 item");
        $("#valor-miniresumo").text( "R$ " + totalcompra);
    }else{
        $("#qtd-miniresumo").text("Nenhum item");
        $("#valor-miniresumo").text("");
    }
}



function addsabor(codsabor,pedaco,simpla) {
    //ADICIONA SABOR NA PIZZA - ATUALIZA PRECO - BUSCA FOTO
    $.ajax({
        method: "POST",
        url: "/exec/montador/add_sabor/?hashsss="+identsss,
        data: {codsabor: codsabor, pedaco: pedaco},
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){
            pizzaatual = msg.pizza;
            if(simpla == undefined){
                rendPizzaMontagem(msg.pizza);
                rendIngredBox(codsabor,pedaco);
            }else{
                rendSimplaMontagem(msg.pizza);
                rendIngredBox(codsabor,pedaco);
            }
        }else if(msg.res === false){
                            
        }else{

        }
        
       
		//console.log(pizzaatual.qtddsabor);
        if(pizzaatual.qtddsabor == pizzaatual.sabores.length){
            $('#btn-pronto').animateCss('tada');
        }
		
    });
}

function add_borda(codborda,origem) {
    $.ajax({
        type: "POST",
        url: "/exec/montador/add_borda/?hashsss="+identsss,
        data: {codborda: codborda},
        dataType: "json" 
    }).done(function( msg ) {
        if(msg.res === true){
            pizzaatual = msg.pizza;
            if(isimples !== true){
                rendPizzaMontagem(msg.pizza);
            }else{
                rendSimplaMontagem(msg.pizza);
            }
            if(origem == "massa"){
                fechaModalUniv();
            }
            $('#preco-pizzabtn p').animateCss('bounceIn');
        }else if(msg.res === false){
                            
        }else{

        }
    });
}

function fechaModalUniv(tempo){
    var tmpo = 0;
    try{ tmpo = parseInt(tempo); }catch(errw){ tmpo = 0; }

    if(tmpo === 0){ $.pgwModal('close'); }else{
        tmpo = tmpo*1000;
        setTimeout(function(){
            $.pgwModal('close');
        },tmpo);
    }
}

function add_ingrediente(coding, codsabor, pedaco) {
    $('#mask').hide();
    $('.window').hide();
    //ADICIONA INGREDIENTE NO SABOR - ATUALIZA PRECO PIZZA
    $.ajax({
        method: "POST",
        url: "/exec/montador/add_ing/?hashsss="+identsss,
        data: {coding: coding, codsabor: codsabor, pedaco: pedaco},
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){
            fechaModalUniv();
            pizzaatual = msg.pizza;
            setTimeout(function(){
                if(isimples !== true){
                    rendPizzaMontagem(msg.pizza);
                    rendIngredBox(codsabor,pedaco);
                }else{
                    rendSimplaMontagem(msg.pizza);
                    rendIngredBox(codsabor,pedaco);
                }
            },400);
            
        }else if(msg.res === false){
                            
        }else{

        }
    });
}

function getDeliveryE(t){
    if(t === undefined){
        //setTimeout(function(){ $.get( "/delivery45129/" ); }, 8000 );
        //setInterval(function(){ $.get( "/delivery45129/" ); },28000);            
    }else{ //$.get( "/delivery45129/" ); 
	}
}


function add_itemPizza(codbbd,elen){
    $.ajax({
        type: "POST",
        url: "/exec/montador/add_itempizza/?hashsss="+identsss,
        data: {codbbd: codbbd},
        dataType: "json" 
    }).done(function( msg ) {
        if(msg.res === true){
            pizzaatual = msg.pizza;
            if(isimples !== true){
                rendPizzaMontagem(msg.pizza);
            }else{
                rendSimplaMontagem(msg.pizza);
            }
            //$.pgwModal('close');
            $(".finalizapedidoMD").show();
            $(".linkitensmsl").removeClass("itemselecionado");
            elen.addClass("itemselecionado");
        }else{
            alert(msg.msg);
            $(".finalizapedidoMD").hide();
        }
    });
}
function getItemVC(iditem){
    var cntitens = listavcitens.length;
    try {    
        iditem = parseInt(iditem);
        for(var i=0; i<cntitens; i++){
            var iditemlista = parseInt(listavcitens[i].item_id);
            if(iditemlista === iditem){
                return listavcitens[i];
            }
        }
    }catch (een){  }
    return null;
}

function rendVCitens(pizza){
    var tamselect = parseInt(pizza.tamanho);
    var contitensvc = listavcitens.length;
    var htmvc = "";
    if(contitensvc > 0){
        for(var i=0; i<contitensvc; i++){
            var tamvc = parseInt(listavcitens[i].tamanho_id);
            if(tamselect === tamvc){
                var iditemvc = listavcitens[i].item_id;
                var nomeitemvc = listavcitens[i].item_nome;
                var precoitemvc = parseFloat(listavcitens[i].item_preco);
                var idfotoitemvc = listavcitens[i].item_fotoid;
                var nomefotoitemvc = listavcitens[i].item_fotonome;
                precoitemvc = (precoitemvc > 0)? "R$ " + parseReal(precoitemvc) : "Grátis";
                
                var classsel = (pizzaatual.cod_itemvendacasada == iditemvc)? " itemselecionado" : "";
                htmvc += "<a class='linkitensmsl"+classsel+"' data-coditem='"+iditemvc+"' href='#'><img src='"+urlsfiles.imagens+"produtos/"+idfotoitemvc+"/60/"+nomefotoitemvc+"' /><span>"+nomeitemvc+"</span><br><small>"+precoitemvc+"</small></a>";
                if(classsel !== ""){
                    $(".finalizapedidoMD").show();
                }
            }
        }
    }
    
    //////console.log(htmvc);
    $("#cont_listitens").html(htmvc);
}


function limpa_box_ingredientes(){
    $('#tit-listaing').text("Ingredientes");
    $('#cont_ingredientes').html("<ul><li><p class='ing'>Selecione um Sabor para Editar os Ingredientes</p></li></ul>");
    $("#adding").html("");
}


function deletar_sabor(sabor, pedaco) {
    $.ajax({
        method: "POST",
        url: "/exec/montador/del_sabor/?hashsss="+identsss,
        data: {codsabor: sabor, pedaco: pedaco},
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){
            pizzaatual = msg.pizza;
            if(isimples !== true){
                rendPizzaMontagem(msg.pizza);
            }else{
                rendSimplaMontagem(msg.pizza);
            }
        }else if(msg.res === false){
                            
        }else{

        }
    });
}


function deletar_ing(codsabor, coding, pedaco, elen) {
    $.ajax({
        method: "POST",
        url: "/exec/montador/remov_ing/?hashsss="+identsss,
        data: {codsabor: codsabor, coding: coding, pedaco: pedaco},
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){
            pizzaatual = msg.pizza;
            elen.addClass("btn-inativo");
            elen.removeClass("btn-ativo"); 
        }else if(msg.res === false){
                            
        }else{

        }
    });
}

function deletar_ingadd(codsabor, coding, pedaco, elen) { //DELETA INGREDIENTE ADICIONADO
    $.ajax({
        method: "POST",
        url: "/exec/montador/del_ingredienteadd/?hashsss="+identsss,
        data: {codsabor: codsabor, coding: coding, pedaco: pedaco},
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){
            pizzaatual = msg.pizza;
            if(isimples !== true){
                rendPizzaMontagem(msg.pizza);
            }else{
                rendSimplaMontagem(msg.pizza);
            }
            var elremov = elen.parent();
            elremov.parent().remove();
        }else if(msg.res === false){
                            
        }else{

        }
    });
}

function retornar_ing(codsabor, coding, pedaco, elen) {
    $.ajax({
        type: "POST",
        url: "/exec/montador/retorna_ing/?hashsss="+identsss,
        data: {codsabor: codsabor, coding: coding, pedaco: pedaco},
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){
            pizzaatual = msg.pizza;   
            elen.addClass("btn-ativo");
            elen.removeClass("btn-inativo");
        }else if(msg.res === false){
                            
        }else{

        }
    });
}

function Ancora(id) {
    $('html,body').animate({scrollTop: $("#" + id).offset().top}, 'slow');
}

function popDdBordas(){
    var cotbrds = ddBordasw.length;
    var tampzzat = "precotam"+pizzaatual.tamanho;
    var cntsd = 0;
    for(var i=0;i<cotbrds;i++){
        if(ddBordasw[i][tampzzat] != undefined){
            ddBordas[cntsd] = {
                borda_id : ddBordasw[i].borda_id,
                borda_nome : ddBordasw[i].borda_nome,
                selected : false,
                borda_preco : ddBordasw[i][tampzzat],
                value : ddBordasw[i].borda_id,
                text : ddBordasw[i].borda_nome+ " + R$ "+ddBordasw[i][tampzzat]
            };
        }
        cntsd++;
    }
}

function gerabordaselect(){
    
    popDdBordas();
    if(ddBordas.length > 0){
        if(ddBordas.length > 4){ 
            ////console.log("aquuuu");
            $('#sel-borda').ddslick('destroy');
            $('#sel-borda').addClass("link-sel-borda");
            $("#sel-borda").html("Adicionar Borda Recheada");
            $("#sel-borda").show();
            popListadeBordas();
        }else{
            $('#sel-borda').ddslick('destroy');
            $("#sel-borda").show();
            $('#sel-borda').removeClass("link-sel-borda");                            
            $('#sel-borda').ddslick({
                data:ddBordas,
                width:265,
                selectText: "Adicionar Borda Recheada",
                onSelected: function(borda){ 
                    var bord = eval(borda.selectedData.value);
                    add_borda(bord);
                    $('#preco-pizzabtn p').animateCss('bounceIn');
                }  
            });
        }    
    }else{
        $('#sel-borda').ddslick('destroy');
        $("#sel-borda").hide();
        $('#sel-borda').removeClass("link-sel-borda");       
    }
}

function popMassa(){
    var htmmass = "";
    var contmss = listamassa.length;
    var tampzzat = "precotam"+pizzaatual.tamanho;
    for(var oik=0; oik<contmss;oik++){
        if(listamassa[oik][tampzzat] != undefined){
            var nomemassa = (listamassa[oik][tampzzat]>0)? listamassa[oik].item_nome + " + R$ "+listamassa[oik][tampzzat]  : listamassa[oik].item_nome;
            var txtavso = (listamassa[oik].item_aceitaborda === "N")? "<br><small class='miniavz'>(esta opção não permite adição de borda.)</small>" : "";
            htmmass += "<li class='itemlistaqtd listamassa'><a href='#' class='selectmassa' data-codmassa='"+listamassa[oik].item_id+"'><span class='qtddsab'><small>"+nomemassa+"</small>"+txtavso+"</span></a></li>";
        }
    }
    //massapop
    /*foreach ($massaspizza as $key => $value) {
        $txtavso = ($value["item_aceitaborda"] === "N")? "<br><small class='miniavz'>(esta opção não permite adição de borda.)</small>" : "";
        echo "<li class='itemlistaqtd listamassa'><a href='#' class='selectmassa' data-codmassa='{$value["item_id"]}'><span class='qtddsab'><small>{$value["item_nome"]}</small>{$txtavso}</span></a></li>";
    }
    */
    $(".massapop").html(htmmass);
}

function popListadeBordas(){
    
    var htmlistabrds = "";
    var iddaborda = "";
    var nomethisborda = "";
    var precothisborda = 0;
    var contbrds = ddBordas.length;
    for(var ik=0;ik<contbrds;ik++){
        nomethisborda = ddBordas[ik].borda_nome;
        precothisborda = ddBordas[ik].borda_preco;
        iddaborda = ddBordas[ik].borda_id;
        nomethisborda = (precothisborda>0)? nomethisborda + " + R$ "+precothisborda : nomethisborda;
        htmlistabrds += "<li class='itemlistaqtd listamassa'><a href='#' class='selectbrd' data-codbrd='"+iddaborda+"'><span class='qtddsab'><small>"+nomethisborda+"</small></span></a></li>";
        
    }
    $(".bordaslista").html(htmlistabrds);
}

function del_borda(cod_borda) {
    $.ajax({
        method: "POST",
        url: "/exec/montador/del_borda/?hashsss="+identsss,
        data: {codborda: cod_borda},
        dataType: "json"
    }).done(function( msg ) {
         if(msg.res === true){
            pizzaatual = msg.pizza;
            if(isimples !== true){
                rendPizzaMontagem(msg.pizza);
            }else{
                rendSimplaMontagem(msg.pizza);
            }
            //$('#sel-borda').ddslick('select', {index: 0 });
            //add_borda(1);
            /*$('#sel-borda').ddslick('destroy');
            $('#sel-borda').ddslick({
                data:ddBordas,
                width:265,
                selectText: "Selecione sua borda",
                onSelected: function(borda){ 
                    var bord = eval(borda.selectedData.value);
                    add_borda(bord);
                    excborda = 1;
                }  
            });*/
            gerabordaselect();
        }else if(msg.res === false){
                            
        }else{

        }
    });
}

function resetPizza(){
    $.ajax({
        method: "POST",
        url: "/exec/montador/reset_pizza/?hashsss="+identsss,
        data: {codesdpizzas: "Hs34sAAkd"},
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){            
            pizzaatual = msg.pizza;            
            resetMontadorPizza();
            $('#opcoespizza').animateCss('zoomOut'); /// 
        }else if(msg.res === false){
                            
        }else{

        }
    });
}

/********************************************************************************************************************************************************/
/***** BEBIDAS ***********/
function addicionaBebida(cod) {
    $.ajax({
        method: "POST",
        url: "/exec/pedido/add_bebida/?hashsss="+identsss,
        data: {cod: cod},
        dataType : "json"
    }).done(function( msg ) {
        if(msg.res === true){            
            resumoitenspedd = msg.resumo;
            rendResumo(resumoitenspedd);
            atualizaMiniResumo();
            animasaoadditem();
        }else if(msg.res === false){            
            resumoitenspedd = msg.resumo;
            rendResumo(resumoitenspedd);
            atualizaMiniResumo();
        }else{
            
        }
    });
}

function ativrVerificacaoPedidoON(){
    //pedido_online();
    setInterval(function(){
        pedido_online();
    }, 45000); //a cada 1min
}

function pedido_online() {
    //Atualiza campo informando que pedido em edição está online
    $.ajax({
        url: "/exec/sistema/sistema_on/?hashsss="+identsss,
        dataType: "json"
    }).done(function(msg){
        if(msg.res === true && msg.aberto === true){
            $(".avisoatendimentofora").removeClass("avisoativo");
        }else{
            $(".avisoatendimentofora").addClass("avisoativo");
        }
    });
}

function getCategSelecionado(){
    if(pizzaatual.sabores != undefined){
        
        if(pizzaatual.sabores.length>0){
            var iddosabor = pizzaatual.sabores[0].idsabor;
            var ctntdsabor = todossabores.length;
            for(var i=0;i<ctntdsabor;i++){
                if(todossabores[i].sabor_id == iddosabor){
                    return todossabores[i].categoria_id;
                }
            }
            
        }        
    }
    return false;
}


function renderListaPizzas(tampizza, pedaco, qtdsabor) {
	
    var contSabores = todossabores.length;
    
    //var catsaborid =  todossabores[0].categoria_id;
    
    var categoria_sabor = todossabores[0].categoria_nome;
    var conzero = 0;
    
    
	var nometipo = (pizzaatual.calzone == 'S')? "Calzone" : "Pizza";
	
	var htmlListaSabores = '<p class="catsabores"> '+nometipo+' ' + categoria_sabor + '</p> <ul>';
    //var idcatselec = getCategSelecionado();
    
    for (var i = 0; i < contSabores; i++) {
        
        
        
        if (tampizza == todossabores[i].tamanho_id) {
            
            //if(idcatselec == false || idcatselec == todossabores[i].categoria_id){

                if (categoria_sabor != todossabores[i].categoria_nome) {
                    if(conzero === 0){
                        htmlListaSabores = '<p class="catsabores"> '+nometipo+' ' + todossabores[i].categoria_nome + '</p> <ul>';
                    }else{
                        htmlListaSabores += '<p class="catsabores"> '+nometipo+' ' + todossabores[i].categoria_nome + '</p>';
                    }
                }
                conzero++;
                var idssbor = todossabores[i].sabor_id;
                var idft = todossabores[i].foto_id;
                var nomeftsab = todossabores[i].foto_sabor;
                var nomesabor = todossabores[i].sabor_nome;
                var prpizzatam = todossabores[i].preco_pizza_tamanho;
                var listaIngsab = todossabores[i].ingredientes_lista;
                var urlfoto = "";
                if(todossabores[i].tamanho_calzone === "S"){
                    urlfoto = ''+urlsfiles.media+vsao+'/img/calzzone.png';
                }else if(nomeftsab != null){
                    urlfoto = ''+urlsfiles.imagens+'produtos/'+ idft + '/96/' + nomeftsab;
                }else {
                    urlfoto = urlsfiles.imagens+'produtos/pizza-ilustrativa.png';

                }

                htmlListaSabores += '<li class="selecSabor" data-idsabor="' + idssbor + '" data-pedaco="'+pedaco+'" >'; //verificar nome campo sabor
                htmlListaSabores += '<div id="foto_sabor"><img class="redonda" src="'+urlfoto+'"/></div>';
                htmlListaSabores += '<div id="dados_sabor">';
                htmlListaSabores += '<p class="lnome_sabor">' + nomesabor + ' - R$ ' + prpizzatam + '</p>';

                htmlListaSabores += '<p class="lingredientes">' + listaIngsab + '</p>';
                htmlListaSabores += '</div>';
                htmlListaSabores += '<div id="clear"></div></li>';
                categoria_sabor = todossabores[i].categoria_nome;
            //}
        }
    }
    htmlListaSabores += "</ul>";
    return htmlListaSabores;
}

function renderListaIngredOpcionais(codsabor, pedaco) {
    var contIngred = listaingredientesopcionais.length;
    var tamanhoat = "precotam"+pizzaatual.tamanho;
    var qtddsabat = pizzaatual.qtddsabor;
    var htmListaIng = "<ul class='listaopcionais'>";
    if(contIngred > 0){        
        for (var i=0; i<contIngred; i++){
            if(listaingredientesopcionais[i][tamanhoat] != undefined){
                var precoopcional = listaingredientesopcionais[i][tamanhoat];
                precoopcional = (precoopcional > 0)? precoopcional/qtddsabat : precoopcional;
                precoopcional = parseReal(precoopcional);
                htmListaIng += '<li data-ped="'+pedaco+'" data-iding="'+ listaingredientesopcionais[i].ingrediente_id +'" data-idsabor="'+ codsabor +'">R$ '+ precoopcional +' - '+ listaingredientesopcionais[i].ingrediente_nome +'</li>';
            }
        }
    }else{
        htmListaIng += '<li>Nenhum Ingrediente Disponível</li>';
    }
    htmListaIng += "</ul>";
    return htmListaIng;
}

function rendResumo(resumo){

    var htmResumo = "";
    var contBebida = resumo.bebidas.length;
    var contPizza = resumo.pizzas.length;
    
    var taxaent = 0;
    try{
        taxaent = parseFloat(resumo.taxadeentrega);
    }catch (e){
        taxaent = 0;
    }
    
    var totalcompra = parseReal(resumo.valortotal);
    
    if(contPizza > 0){

        for( var p = 0; p < contPizza; p++){
            var brindepizza = "";
            var bordaspizza = "";
            var contBordas = resumo.pizzas[p].bordas.length;
            if(contBordas > 0){
                //bordaspizza = '<strong>Borda: </strong>';
                for(var bd = 0; bd < contBordas; bd++){
                    var xbordaspizza = resumo.pizzas[p].bordas[bd].nome;
                    var gshdborda = xbordaspizza.split(":");
                    var nomebordamassa = "<span><strong>"+gshdborda[0]+"</strong>: "+gshdborda[1]+"<span>";
                    bordaspizza+= nomebordamassa;
                    if( (bd+1)!==contBordas ){ bordaspizza+= ", "; }                               
                }
            }
            
            var cod = resumo.pizzas[p].cod;
            var seg = resumo.pizzas[p].seg;
            var skeyitm = resumo.pizzas[p].skeyitm;
            var nomepizzas = "";
            var detalhespizza = '';
            var btndetalhe = '';                        
            var tamanho = resumo.pizzas[p].tamanho;
            var precopizza = parseReal(resumo.pizzas[p].preco);
            var precototalpizza = parseReal(resumo.pizzas[p].precototal);
            var qtddpzz = resumo.pizzas[p].qttdd;                        
            
            //////console.log(resumo.pizzas[p].itemvc);
            
            //nome_item: "Sprite 2 Lts", nome_categoria: "Refrigerante", preco_item: 0
            //var contbrinde = resumo.pizzas[p].brinde.length;
            
            if(resumo.pizzas[p].itemvc.nome_item !== undefined){
                var idfoto = resumo.pizzas[p].itemvc.cod_foto;
                var nomefoto = resumo.pizzas[p].itemvc.nome_foto;
                var fotobrinde = (idfoto != null)? ""+urlsfiles.imagens+"produtos/"+idfoto+ "/40/"+nomefoto : "";
                var tipobrinde = resumo.pizzas[p].itemvc.nome_categoria;
                var nomebrinde = resumo.pizzas[p].itemvc.nome_item;
                var precobrinde = resumo.pizzas[p].itemvc.preco_item;
                brindepizza = "<div class='bindpizzas'>"
                    +           "<div class='fotobrinde'><img src='"+fotobrinde+"' /></div>";
                if(precobrinde == 0){
                    brindepizza += "<h3 class='titlebrinde'>Brinde</h3>";
                }
                brindepizza += "<div class='infobrinde'><strong>"+nomebrinde+"</strong><small> (<span class='qtddbrind'>"+qtddpzz+"<span> - "+tipobrinde+")</small></div>"
                    +       "</div>";
            }
            
            var contSabor = resumo.pizzas[p].sabor.length;

            for( var s = 0; s < contSabor; s++ ){
                var nomesabor = resumo.pizzas[p].sabor[s].nome;                            
                nomepizzas += nomesabor;                            

                var contIngAdd = resumo.pizzas[p].sabor[s].ingcom.length;
                var contIngRem = resumo.pizzas[p].sabor[s].ingrem.length;

                if(contIngAdd > 0 || contIngRem > 0){

                    if(detalhespizza === ''){
                        detalhespizza = '<span class="det-pizza-ped">';
                    }                                
                    detalhespizza += '<strong>'+nomesabor+': </strong>';

                    for(var irem = 0; irem < contIngRem; irem++){
                        var ingrem = resumo.pizzas[p].sabor[s].ingrem[irem].nome;                                    
                        detalhespizza += 's/ '+ ingrem;
                        if( (irem+1)!==contIngRem ){ detalhespizza+= ", "; }
                    }

                    if(contIngAdd > 0 && contIngRem > 0){ detalhespizza+= ", "; }

                    for(var iadd = 0; iadd < contIngAdd; iadd++){
                        var ingadd = resumo.pizzas[p].sabor[s].ingcom[iadd].nome;                                    
                        detalhespizza += 'c/ '+ ingadd;
                        if( (iadd+1)!==contIngAdd ){ detalhespizza+= ", "; }
                    }                                  
                }                            

                if( (s+1)!==contSabor ){
                    nomepizzas += " + "; 
                    if(detalhespizza !== ''){
                        detalhespizza += "<br>";
                    }
                }else{
                    nomepizzas += "<br>"; 
                }
            }
            
            if(detalhespizza !== ''){
                detalhespizza += '</span>';
                btndetalhe = '<div class="det-edt-item-ped det-ped-item">'
                            +    'Detalhes'
                            +'</div>'
                            +'<div class="det-edt-item-ped det-esc-ped-item" >'
                            +    'Detalhes'
                            +'</div>';
            }                      
            
            var icopizza = (resumo.pizzas[p].calzone === "S")? ""+urlsfiles.media+vsao+"/img/icon-pizza-pedido.png" : ""+urlsfiles.media+vsao+"/img/"+resumo.pizzas[p].icone;
            //'<img src="'+urlsfiles.imagens+'produtos/'+resumo.bebidas[b].idimg+'/60/'+resumo.bebidas[b].foto+'">'
            htmResumo += '<div class="item-pedido">'
                        +    '<div class="resumo-item">'
                        +        '<div class="item-imagem">'
                        +            '<img src="'+icopizza+'">'
                        +        '</div>'
                        +        '<div class="item-precoeqtdd">'
                        +            '<div class="qtdd-item-ped">'
                        +                '<a class="qtdd-item-ped-menosum" data-seg="'+seg+'" data-skeyitm="'+skeyitm+'" data-cod="'+cod+'" href="#"></a>'
                        +                '<input type="text" class="in-qtdd-item-ped" readonly="on" value="'+qtddpzz+'" />'
                        +                '<a class="qtdd-item-ped-maisum" data-seg="'+seg+'" data-skeyitm="'+skeyitm+'" data-cod="'+cod+'" href="#"></a>'
                        +            '</div>'
                        +        '</div>'
                        +        '<p class="tam-pizza-ped"><span class="remov-item-ped" data-seg="'+seg+'" data-skeyitm="'+skeyitm+'" data-cod="'+cod+'" >x</span>'+tamanho+'</p>'
                        +        '<p class="nome-item-ped">'
                        +            nomepizzas //'4 Queijos com Bacon + Frango com Requijão Cremoso + Banana com açúcar e canela<br>'
                        +            bordaspizza
                        +            detalhespizza
                        +        '</p>'
                        +       brindepizza
                        +       '<div style="width:100%;height:1px;display:block;float:left;"></div>'
                        +        btndetalhe;
                if(resumo.pizzas[p].permiteeditar){
                        htmResumo +='<div class="det-edt-item-ped edt-ped-item editaPizza" data-seg="'+seg+'" data-skeyitm="'+skeyitm+'" data-cod="'+cod+'" >'
                        +            'Editar'
                        +        '</div>';
                }
                        htmResumo +='<div class="preco-item-ped preco-itempizza-ped">'
                        +            'R$ <span>'+precopizza+'</span>'
                        +        '</div>'
                        +    '</div>'
                        +'</div>';
        }                    
    }
    
    if(contBebida > 0){

        for( var b=0; b<contBebida; b++){

            var precobebida = parseReal(resumo.bebidas[b].preco);
            var precototalbebida = parseReal(resumo.bebidas[b].precototal);
            var cod = resumo.bebidas[b].cod;
            //var preco = resumo.bebidas[b].preco;
            var seg = resumo.bebidas[b].seg;
            var skeyitm = resumo.bebidas[b].skeyitm;
            htmResumo += '<div class="item-pedido">'
                            +'<div class="resumo-item">'
                            +    '<div class="item-imagem imgitemsimples-ped">'
                            +        '<img src="'+urlsfiles.imagens+'produtos/'+resumo.bebidas[b].idimg+'/60/'+resumo.bebidas[b].foto+'">'
                            +    '</div>'
                            +    '<div class="item-precoeqtdd">'
                            +        '<div class="qtdd-item-ped">'
                            +            '<a class="qtdd-item-ped-menosum" data-seg="'+seg+'" data-skeyitm="'+skeyitm+'" data-cod="'+cod+'" href="#"></a>'
                            +            '<input type="text" class="in-qtdd-item-ped" readonly="on" value="'+resumo.bebidas[b].qtdd+'" />'
                            +            '<a class="qtdd-item-ped-maisum" data-seg="'+seg+'" data-skeyitm="'+skeyitm+'" data-cod="'+cod+'" href="#"></a>'
                            +        '</div>'
                            +        '<div class="preco-item-ped">'
                            +            'R$ <span>'+ precobebida +'</span>'
                            +        '</div>'
                            +    '</div>'
                            +    '<p class="tam-pizza-ped itemsimples-ped"><span class="remov-item-ped" data-seg="'+seg+'" data-skeyitm="'+skeyitm+'" data-cod="'+cod+'" >x</span>'+ resumo.bebidas[b].nome  +'</p>'
                            +'</div>'
                        +'</div>';
        }
    }
    
    
    if(htmResumo == ""){                
        htmResumo = "<div class='car-sem-item'> <img src='"+urlsfiles.media+vsao+"/img/emot-fome.png' /> <img style='margin-top: 50px;' src='"+urlsfiles.media+vsao+"/img/seta-add-item.png' /> </div> ";
        $("#total-finaliza-ped").hide();
    }else{
        $("#total-finaliza-ped").show();
    }
    
    
    //////console.log(resumo.desconto);
    if(eval(resumo.desconto) > 0){
        $("#sub_desc").show();
        $(".subTotaoped").text("Subtotal R$ "+parseReal(resumo.subtotal));
        $(".descontoTotalped").text("Desconto R$ "+parseReal(resumo.desconto));
        $("#txttotal").addClass("totalverde");
        $("#txttotal").css("margin-bottom","0px");
    }else{
        $("#txttotal").css("margin-bottom","15px");
        $("#txttotal").removeClass("totalverde");
        $("#sub_desc").hide();
    }
    
    if(resumo.promoitem === "pizza"){
        setTimeout(function(){
            showModalItemPizza();
        },500);        
    }else if(resumo.promoitem === "refri"){
        setTimeout(function(){
            showModalItemRefri();
        },500);
    }
    
    if(taxaent > 0){
        $("#sub_taxaent").show();
        $("#valtaxa").text("R$ "+parseReal(taxaent));
        $(".bl-taxa").text("Taxa de entrega: R$ "+parseReal(taxaent));
    }else{
        
        $("#sub_taxaent").hide();
        $("#valtaxa").text("R$ 0,00");
        if(resumo.tipoentrega === "E"){
            $(".bl-taxa").text("Taxa de entrega: Gratis");
        }
    }
    var xpedidomin = $("#valominpedido").data("valorminimopedido");
    if(xpedidomin < resumo.valortotal){
        $("#valominpedido").hide();
        $(".btn-comprar.btn-finalizar").show();
    }else{
        $("#valominpedido").show();
        $(".btn-comprar.btn-finalizar").hide();
    }
    
    $("#allitens").find(".item-pedido").remove();
    $("#allitens").html(htmResumo);
    $("#totalrs-ped").text(totalcompra);
    atualizaMiniResumo();
}

function rendEndereco(dados,atualiza){
    
    var htmEnderecos = "";

    var idEnd = dados.endereco_id;
    var titlEnd = dados.endereco_titulo;
    var logradouroEnd = dados.endereco_logradouro;
    var bairroEnd = dados.endereco_bairro;
    var numeroEnd = dados.endereco_numero;
    var codcidEnd = dados.endereco_codcidade;
    var cidadeufEnd = dados.endereco_cidadeUF;
    var cepEnd = dados.endereco_cep;
    var complementoEnd = dados.endereco_complemento;
    var principalEnd = dados.endereco_principal;
    var clprin = "";
    if(principalEnd === "S"){
        clprin = "endprincipal";
    }

    titlEnd = (titlEnd !== null && principalEnd !== 'S')? titlEnd : "Endereco Principal";

    var enderecocompleto = logradouroEnd;
    enderecocompleto += (numeroEnd !== null && numeroEnd !== "")? ", nº " + numeroEnd : "";
    enderecocompleto += (complementoEnd !== null && complementoEnd !== "")? " ( "+complementoEnd+" ) " : "" ;
    enderecocompleto += ", " + bairroEnd;
    enderecocompleto += " - " + cidadeufEnd;
    //enderecocompleto += (cepEnd !== null && cepEnd !== "")? " - CEP: " + cepEnd : "";

    if(atualiza === undefined){
        htmEnderecos += "<div class='linha_endereco "+ clprin+ "' data-idendereco='" +idEnd+ "' data-enderecocompleto='" +JSON.stringify(dados)+ "'>" ;
    }else{
        $(".linha_endereco[data-idendereco='"+idEnd+"']").data("enderecocompleto",dados);
    }
    htmEnderecos += "<strong>"+titlEnd + "</strong><br>"
                + "<span>"+enderecocompleto+ "</span>"   
                + "<a class='removerendereco' href='#' title='Excluir Endereço'><img src='data:image/svg+xml;utf8;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iaXNvLTg4NTktMSI/Pgo8IS0tIEdlbmVyYXRvcjogQWRvYmUgSWxsdXN0cmF0b3IgMTYuMC4wLCBTVkcgRXhwb3J0IFBsdWctSW4gLiBTVkcgVmVyc2lvbjogNi4wMCBCdWlsZCAwKSAgLS0+CjwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9FTiIgImh0dHA6Ly93d3cudzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCI+CjxzdmcgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB4bWxuczp4bGluaz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94bGluayIgdmVyc2lvbj0iMS4xIiBpZD0iQ2FwYV8xIiB4PSIwcHgiIHk9IjBweCIgd2lkdGg9IjE2cHgiIGhlaWdodD0iMTZweCIgdmlld0JveD0iMCAwIDQwOC40ODMgNDA4LjQ4MyIgc3R5bGU9ImVuYWJsZS1iYWNrZ3JvdW5kOm5ldyAwIDAgNDA4LjQ4MyA0MDguNDgzOyIgeG1sOnNwYWNlPSJwcmVzZXJ2ZSI+CjxnPgoJPGc+CgkJPHBhdGggZD0iTTg3Ljc0OCwzODguNzg0YzAuNDYxLDExLjAxLDkuNTIxLDE5LjY5OSwyMC41MzksMTkuNjk5aDE5MS45MTFjMTEuMDE4LDAsMjAuMDc4LTguNjg5LDIwLjUzOS0xOS42OTlsMTMuNzA1LTI4OS4zMTYgICAgSDc0LjA0M0w4Ny43NDgsMzg4Ljc4NHogTTI0Ny42NTUsMTcxLjMyOWMwLTQuNjEsMy43MzgtOC4zNDksOC4zNS04LjM0OWgxMy4zNTVjNC42MDksMCw4LjM1LDMuNzM4LDguMzUsOC4zNDl2MTY1LjI5MyAgICBjMCw0LjYxMS0zLjczOCw4LjM0OS04LjM1LDguMzQ5aC0xMy4zNTVjLTQuNjEsMC04LjM1LTMuNzM2LTguMzUtOC4zNDlWMTcxLjMyOXogTTE4OS4yMTYsMTcxLjMyOSAgICBjMC00LjYxLDMuNzM4LTguMzQ5LDguMzQ5LTguMzQ5aDEzLjM1NWM0LjYwOSwwLDguMzQ5LDMuNzM4LDguMzQ5LDguMzQ5djE2NS4yOTNjMCw0LjYxMS0zLjczNyw4LjM0OS04LjM0OSw4LjM0OWgtMTMuMzU1ICAgIGMtNC42MSwwLTguMzQ5LTMuNzM2LTguMzQ5LTguMzQ5VjE3MS4zMjlMMTg5LjIxNiwxNzEuMzI5eiBNMTMwLjc3NSwxNzEuMzI5YzAtNC42MSwzLjczOC04LjM0OSw4LjM0OS04LjM0OWgxMy4zNTYgICAgYzQuNjEsMCw4LjM0OSwzLjczOCw4LjM0OSw4LjM0OXYxNjUuMjkzYzAsNC42MTEtMy43MzgsOC4zNDktOC4zNDksOC4zNDloLTEzLjM1NmMtNC42MSwwLTguMzQ5LTMuNzM2LTguMzQ5LTguMzQ5VjE3MS4zMjl6IiBmaWxsPSIjNDQ0NDQ0Ii8+CgkJPHBhdGggZD0iTTM0My41NjcsMjEuMDQzaC04OC41MzVWNC4zMDVjMC0yLjM3Ny0xLjkyNy00LjMwNS00LjMwNS00LjMwNWgtOTIuOTcxYy0yLjM3NywwLTQuMzA0LDEuOTI4LTQuMzA0LDQuMzA1djE2LjczN0g2NC45MTYgICAgYy03LjEyNSwwLTEyLjksNS43NzYtMTIuOSwxMi45MDFWNzQuNDdoMzA0LjQ1MVYzMy45NDRDMzU2LjQ2NywyNi44MTksMzUwLjY5MiwyMS4wNDMsMzQzLjU2NywyMS4wNDN6IiBmaWxsPSIjNDQ0NDQ0Ii8+Cgk8L2c+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPC9zdmc+Cg==' /></a>"
                + "<a class='editarendereco' href='#' title='Editar Endereço'><img src='data:image/svg+xml;utf8;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iaXNvLTg4NTktMSI/Pgo8IS0tIEdlbmVyYXRvcjogQWRvYmUgSWxsdXN0cmF0b3IgMTYuMC4wLCBTVkcgRXhwb3J0IFBsdWctSW4gLiBTVkcgVmVyc2lvbjogNi4wMCBCdWlsZCAwKSAgLS0+CjwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9FTiIgImh0dHA6Ly93d3cudzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCI+CjxzdmcgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB4bWxuczp4bGluaz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94bGluayIgdmVyc2lvbj0iMS4xIiBpZD0iQ2FwYV8xIiB4PSIwcHgiIHk9IjBweCIgd2lkdGg9IjE2cHgiIGhlaWdodD0iMTZweCIgdmlld0JveD0iMCAwIDUxMiA1MTIiIHN0eWxlPSJlbmFibGUtYmFja2dyb3VuZDpuZXcgMCAwIDUxMiA1MTI7IiB4bWw6c3BhY2U9InByZXNlcnZlIj4KPGc+Cgk8cGF0aCBkPSJNNDQ4LDE3Ny4xNFY0NDhjMCwzNS4zNDQtMjguNjU2LDY0LTY0LDY0SDY0Yy0zNS4zNDQsMC02NC0yOC42NTYtNjQtNjRWMTI4YzAtMzUuMzQ0LDI4LjY1Ni02NCw2NC02NGgyNzAuODQ0bC02My45NjksNjQgICBINjR2MzIwaDMyMFYyNDEuMTU2TDQ0OCwxNzcuMTR6IE0zOTguODc1LDQ1LjI1TDM3Ni4yNSw2Ny44NzVsNjcuODc1LDY3Ljg5MWwyMi42MjUtMjIuNjI1TDM5OC44NzUsNDUuMjV6IE00NDQuMTI1LDAgICBMNDIxLjUsMjIuNjI1bDY3Ljg3NSw2Ny44OTFMNTEyLDY3Ljg3NUw0NDQuMTI1LDB6IE0xNTAsMjk0LjE4OGw2Ny44NzUsNjcuODc1TDQyMS41LDE1OC40MDZsLTY3Ljg3NS02Ny44OTFMMTUwLDI5NC4xODh6ICAgIE0xMjgsMzg0aDY0bC02NC02NFYzODR6IiBmaWxsPSIjNDQ0NDQ0Ii8+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPGc+CjwvZz4KPC9zdmc+Cg==' /></a>";
    if(atualiza === undefined){
        htmEnderecos += "</div>";
        $("#allenderecos").append(htmEnderecos);
    }else{
        $(".linha_endereco[data-idendereco='"+idEnd+"']").html(htmEnderecos);
    }
}