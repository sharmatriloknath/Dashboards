$(document).ready(function(){
    //console.log("Testing");
    function kanban_merger(onlyForOne,searchedKey='NA',timeVal=1300)
    {
        var tempUrl = window.location.hash;
//        console.log("TempUrl",tempUrl);
        if(tempUrl.indexOf('model=purchase.extension.dashboard.testing') > -1){
            var tempDict = {};
            var refSelector = '.o_kanban_dashboard .o_kanban_record:visible:not(.o_kanban_ghost)';
            if(onlyForOne){
                refSelector = '.o_kanban_dashboard .o_kanban_record:not(.o_kanban_ghost)';
            }
            setTimeout(function(){
//                console.log("Total length:",$('.o_kanban_dashboard .o_kanban_record:not(.o_kanban_ghost)').length);
                $(refSelector).each(function(){

                    var key = $(this).find(".o_kanban_record_headings").text().trim();

                    if(onlyForOne && searchedKey != key && Object.keys(tempDict).indexOf(searchedKey) > -1){
                        return false;
                    }

                    var val = $(this).find('.o_kanban_card_content .row').html();
                    //var val = $(this).find('.o_kanban_card_content .row').text().trim();
                    if(Object.keys(tempDict).indexOf(key) < 0){
//                        console.log('Keys',key)
                        tempDict[key] = [val];
                    }
                    else{
                        tempDict[key].push(val);
                        $(this).css('display','none');
//                        $(this).remove();
                    }

                });
//                console.log("full dict",tempDict);

                $('.o_kanban_dashboard .o_kanban_record:visible:not(.o_kanban_ghost)').each(function(){
                    var key = $(this).find(".o_kanban_record_headings").text().trim();
//                    var valList = tempDict[key];
//
//                    for(var i = 1; i<valList.length; i++){
//                        $(this).find('.o_kanban_card_content .row').append(valList[i]);
//                    }
                    if(onlyForOne && searchedKey == key)
                    {
                        $(this).find('.o_kanban_card_content .row').html(tempDict[key].join(' '));
                        return false;
                    }
                    else{
                        $(this).find('.o_kanban_card_content .row').html(tempDict[key].join(' '));
                    }


                });

            },timeVal);


        }

    }


    $(window).on('hashchange', function(){
        kanban_merger(onlyForOne=false)
    });
    $('div[data-menu-xmlid="purchase_extension_dashboard.purchase_menu_board_testing"] a').on('click',function(){
        kanban_merger(onlyForOne=false);
    });
    $(document).on('click','.o_kanban_dashboard .o_kanban_record:visible:not(.o_kanban_ghost) a[data-context="{\'view_type\': 1}"]' ,function(){
        console.log("I am running");
        var searchedKey = $(this).parents(".oe_kanban_global_click").find(".o_kanban_record_headings").text().trim();
        kanban_merger(onlyForOne=true,searchedKey=searchedKey,timeVal=400);
    });


});